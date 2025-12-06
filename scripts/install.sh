#!/usr/bin/env bash
set -euo pipefail

# Simple installer for a fresh Ubuntu/Debian-like system.
# - Installs system dependencies (python3, pip, git, curl)
# - Clones or updates the repo to ~/ai_bridge_app (override with INSTALL_DIR)
# - Installs Python deps with pip --user --break-system-packages
# - Reminds you how to run the server

REPO_URL="https://github.com/davixspain/ai-bridge-app.git"
INSTALL_DIR="${INSTALL_DIR:-$HOME/ai_bridge_app}"
PY_PACKAGES=(fastapi "uvicorn[standard]" httpx pydantic)

command_exists() { command -v "$1" >/dev/null 2>&1; }

echo "==> Ensuring system packages (sudo may prompt you)..."
if command_exists apt-get; then
  sudo apt-get update -y
  sudo apt-get install -y python3 python3-pip git curl
elif command_exists yum; then
  sudo yum install -y python3 python3-pip git curl
else
  echo "Unsupported package manager. Install python3, pip, git, and curl manually, then rerun."
  exit 1
fi

echo "==> Cloning/updating repository into $INSTALL_DIR ..."
if [ -d "$INSTALL_DIR/.git" ]; then
  git -C "$INSTALL_DIR" pull --ff-only
else
  git clone "$REPO_URL" "$INSTALL_DIR"
fi

echo "==> Installing Python packages locally (~/.local)..."
export PATH="$HOME/.local/bin:$PATH"
python3 -m pip install --user --break-system-packages "${PY_PACKAGES[@]}"

cat <<'EOF'

Done.
To run the server:
  export PATH="$HOME/.local/bin:$PATH"
  export N8N_BASE_URL="http://localhost:5678"
  export N8N_API_KEY="<your n8n api key>"
  export LLM_PROVIDER="groq"   # or deepseek
  export GROQ_API_KEY="<your groq key>"  # if groq
  export DEEPSEEK_API_KEY="<your deepseek key>"  # if deepseek
  cd ~/ai_bridge_app
  uvicorn main:app --host 0.0.0.0 --port 8001 --reload

Or use the launcher script:
  cd ~/ai_bridge_app && ./run_ai_bridge.sh

EOF
