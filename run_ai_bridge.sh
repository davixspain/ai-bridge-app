#!/usr/bin/env bash
set -euo pipefail

BASE_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$BASE_DIR"

DEFAULT_BASE_URL="${N8N_BASE_URL:-http://localhost:5678}"
DEFAULT_PROVIDER="${LLM_PROVIDER:-groq}"
DEFAULT_MODEL="${LLM_MODEL:-}"
DEFAULT_N8N_KEY="${N8N_API_KEY:-}"
DEFAULT_GROQ_KEY="${GROQ_API_KEY:-}"
DEFAULT_DEEPSEEK_KEY="${DEEPSEEK_API_KEY:-}"

read -r -p "n8n base URL [${DEFAULT_BASE_URL}]: " N8N_BASE_URL
N8N_BASE_URL="${N8N_BASE_URL:-$DEFAULT_BASE_URL}"

if [[ -z "${DEFAULT_N8N_KEY}" ]]; then
  read -r -s -p "n8n API key (required): " N8N_API_KEY
  echo
else
  read -r -p "n8n API key [hidden, press enter to keep existing]: " tmp </dev/tty || true
  if [[ -n "${tmp:-}" ]]; then
    N8N_API_KEY="$tmp"
  else
    N8N_API_KEY="$DEFAULT_N8N_KEY"
  fi
fi

read -r -p "LLM provider (groq/deepseek) [${DEFAULT_PROVIDER}]: " LLM_PROVIDER
LLM_PROVIDER="${LLM_PROVIDER:-$DEFAULT_PROVIDER}"

if [[ "$LLM_PROVIDER" == "groq" ]]; then
  if [[ -z "${DEFAULT_GROQ_KEY}" ]]; then
    read -r -s -p "Groq API key: " GROQ_API_KEY
    echo
  else
    read -r -p "Groq API key [hidden, press enter to keep existing]: " tmp </dev/tty || true
    if [[ -n "${tmp:-}" ]]; then
      GROQ_API_KEY="$tmp"
    else
      GROQ_API_KEY="$DEFAULT_GROQ_KEY"
    fi
  fi
elif [[ "$LLM_PROVIDER" == "deepseek" ]]; then
  if [[ -z "${DEFAULT_DEEPSEEK_KEY}" ]]; then
    read -r -s -p "DeepSeek API key: " DEEPSEEK_API_KEY
    echo
  else
    read -r -p "DeepSeek API key [hidden, press enter to keep existing]: " tmp </dev/tty || true
    if [[ -n "${tmp:-}" ]]; then
      DEEPSEEK_API_KEY="$tmp"
    else
      DEEPSEEK_API_KEY="$DEFAULT_DEEPSEEK_KEY"
    fi
  fi
fi

if [[ -n "${DEFAULT_MODEL}" ]]; then
  read -r -p "LLM model override [${DEFAULT_MODEL} or empty for default]: " LLM_MODEL
  LLM_MODEL="${LLM_MODEL:-$DEFAULT_MODEL}"
else
  read -r -p "LLM model override (optional, leave empty for provider default): " LLM_MODEL
fi

export PATH="$HOME/.local/bin:$PATH"
export N8N_BASE_URL N8N_API_KEY LLM_PROVIDER LLM_MODEL GROQ_API_KEY DEEPSEEK_API_KEY

echo "Checking n8n at $N8N_BASE_URL ..."
if ! curl -sf -H "X-N8N-API-KEY: $N8N_API_KEY" "$N8N_BASE_URL/api/v1/workflows" >/dev/null; then
  echo "Warning: Unable to reach n8n or auth failed. Continuing anyway."
fi

echo "Starting AI Bridge on http://127.0.0.1:8001 ..."
exec uvicorn main:app --host 0.0.0.0 --port 8001 --reload
