# AI Bridge

FastAPI service that receives a workflow ID plus a natural-language request, fetches the workflow from n8n, optionally lets an LLM modify the JSON, and returns the result.

## One-command install (fresh Ubuntu/Debian)

```bash
bash -c "$(curl -fsSL https://raw.githubusercontent.com/davixspain/ai-bridge-app/main/scripts/install.sh)"
```

This installs system deps, clones/updates to `~/ai_bridge_app`, and installs Python deps locally.

## Configuration (env vars)

- `N8N_BASE_URL` (default `http://localhost:5678`)
- `N8N_API_KEY` (sent as `X-N8N-API-KEY`)
- `LLM_PROVIDER`: `groq` or `deepseek` (omit to disable LLM and just echo the workflow)
- `LLM_MODEL`: optional override (defaults: Groq `llama-3.1-8b-instant`, DeepSeek `deepseek-chat`)
- `GROQ_API_KEY` (if `LLM_PROVIDER=groq`)
- `DEEPSEEK_API_KEY` (if `LLM_PROVIDER=deepseek`)

## Run

```bash
export PATH="$HOME/.local/bin:$PATH"
export N8N_API_KEY=...               # required
export N8N_BASE_URL=http://localhost:5678
export LLM_PROVIDER=groq             # or deepseek; omit to disable
export GROQ_API_KEY=...              # or DEEPSEEK_API_KEY=...

cd /home/d/ai_bridge_app
uvicorn main:app --host 0.0.0.0 --port 8001 --reload
```

## Try it

```bash
curl -X POST http://localhost:8001/apply-change \
  -H "Content-Type: application/json" \
  -d '{"workflowId": "7bp69J0fYkAEvYI7", "userRequest": "change something"}'
```

If `LLM_PROVIDER` is set, the service will call the chosen LLM, PUT the updated workflow back to n8n, and return the modified workflow JSON (plus the n8n save response). Otherwise it returns the original workflow without saving.

## Launcher

If you prefer prompts for env setup and auto-start, use:
```bash
cd /home/d/ai_bridge_app && ./run_ai_bridge.sh
```
