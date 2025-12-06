import json
import os
from typing import Any, Dict, Optional, Union

import httpx
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field


class ApplyChangeRequest(BaseModel):
    workflowId: Union[int, str] = Field(..., description="n8n workflow ID to load and later modify")
    userRequest: str = Field(..., description="User instruction; currently unused and kept for future LLM bridge")


N8N_BASE_URL = os.environ.get("N8N_BASE_URL", "http://localhost:5678")
N8N_API_KEY = os.environ.get("N8N_API_KEY")

LLM_PROVIDER = os.environ.get("LLM_PROVIDER")  # "groq" or "deepseek"
LLM_MODEL = os.environ.get("LLM_MODEL")  # optional override per provider
GROQ_API_KEY = os.environ.get("GROQ_API_KEY") or os.environ.get("GROQ_API")
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY")

DEFAULT_MODELS = {
    "groq": "llama-3.1-8b-instant",  # fast, inexpensive general-purpose
    "deepseek": "deepseek-chat",
}

app = FastAPI(title="AI Bridge", version="0.1.0")


async def fetch_workflow(workflow_id: Union[int, str]) -> Dict[str, Any]:
    """Retrieve a workflow from n8n and surface meaningful errors."""
    headers = {}
    if N8N_API_KEY:
        headers["X-N8N-API-KEY"] = N8N_API_KEY

    url = f"{N8N_BASE_URL.rstrip('/')}/api/v1/workflows/{workflow_id}"
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(url, headers=headers)

    if response.status_code == 404:
        raise HTTPException(status_code=404, detail="Workflow not found")
    if response.is_error:
        raise HTTPException(
            status_code=502,
            detail=f"n8n returned {response.status_code}: {response.text}",
        )

    return response.json()


async def call_llm(workflow: Dict[str, Any], user_request: str) -> Dict[str, Any]:
    """Call configured LLM provider to return an updated workflow JSON."""
    if not LLM_PROVIDER:
        raise HTTPException(status_code=400, detail="LLM_PROVIDER env var not set; cannot modify workflow")

    provider = LLM_PROVIDER.lower()
    if provider == "groq":
        api_key = GROQ_API_KEY
        url = "https://api.groq.com/openai/v1/chat/completions"
        model = LLM_MODEL or DEFAULT_MODELS["groq"]
    elif provider == "deepseek":
        api_key = DEEPSEEK_API_KEY
        url = "https://api.deepseek.com/chat/completions"
        model = LLM_MODEL or DEFAULT_MODELS["deepseek"]
    else:
        raise HTTPException(status_code=400, detail=f"Unsupported LLM_PROVIDER '{LLM_PROVIDER}'")

    if not api_key:
        raise HTTPException(status_code=400, detail=f"API key missing for provider '{provider}'")

    system_prompt = (
        "You are an n8n workflow JSON editor. "
        "Given the current workflow JSON and a user request, return ONLY the updated workflow JSON. "
        "Preserve node IDs, connections, credentials, and metadata unless the user explicitly asks to change them. "
        "If the request is unclear, return the original workflow unchanged. "
        "Output must be valid JSON (an object) with no code fences or prose."
    )
    user_payload = {
        "workflow": workflow,
        "request": user_request,
    }

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": json.dumps(user_payload)},
        ],
        "temperature": 0.0,
    }

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(url, headers=headers, json=payload)

    if resp.status_code == 401:
        raise HTTPException(status_code=401, detail=f"LLM provider auth failed ({provider})")
    if resp.is_error:
        raise HTTPException(status_code=502, detail=f"LLM error {resp.status_code}: {resp.text}")

    data = resp.json()
    content: Optional[str] = (
        data.get("choices", [{}])[0]
        .get("message", {})
        .get("content")
    )
    if not content:
        raise HTTPException(status_code=502, detail="LLM response missing content")

    # Try to parse content as JSON; strip code fences if present.
    cleaned = content.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        # remove possible language hint e.g., json\n
        cleaned = cleaned.split("\n", 1)[-1]
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=502, detail=f"LLM returned non-JSON content: {cleaned}") from exc


async def push_workflow(workflow_id: Union[int, str], workflow: Dict[str, Any]) -> Dict[str, Any]:
    """PUT updated workflow back to n8n."""
    headers = {}
    if N8N_API_KEY:
        headers["X-N8N-API-KEY"] = N8N_API_KEY

    url = f"{N8N_BASE_URL.rstrip('/')}/api/v1/workflows/{workflow_id}"
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.put(url, headers=headers, json=workflow)

    if response.status_code == 404:
        raise HTTPException(status_code=404, detail="Workflow not found when saving")
    if response.is_error:
        raise HTTPException(
            status_code=502,
            detail=f"n8n PUT returned {response.status_code}: {response.text}",
        )

    return response.json()


@app.post("/apply-change")
async def apply_change(request: ApplyChangeRequest) -> Dict[str, Any]:
    """Fetch a workflow from n8n, run it through the LLM (if configured), and return the result."""
    workflow = await fetch_workflow(request.workflowId)

    if not LLM_PROVIDER:
        return {
            "workflowId": request.workflowId,
            "status": "fetched",
            "note": "LLM disabled (set LLM_PROVIDER to 'groq' or 'deepseek'). Returning original workflow.",
            "workflow": workflow,
        }

    updated_workflow = await call_llm(workflow, request.userRequest)

    # Some models may wrap the workflow object; unwrap common pattern.
    if isinstance(updated_workflow, dict) and "workflow" in updated_workflow and isinstance(updated_workflow["workflow"], dict):
        updated_workflow = updated_workflow["workflow"]

    saved = await push_workflow(request.workflowId, updated_workflow)

    return {
        "workflowId": request.workflowId,
        "status": "updated_and_saved",
        "provider": LLM_PROVIDER,
        "saved": True,
        "n8n_response": saved,
        "workflow": updated_workflow,
    }
