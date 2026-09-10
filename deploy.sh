#!/usr/bin/env bash

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="${SCRIPT_DIR}/.env"

if [ ! -f "$ENV_FILE" ]; then
  echo "Error: .env file not found at ${ENV_FILE}"
  echo "Copy .env.example to .env and fill in the values."
  exit 1
fi

set -a
# shellcheck source=.env.example
source "$ENV_FILE"
set +a

: "${DEPLOY_HOST:?DEPLOY_HOST is not set in .env}"
: "${DEPLOY_USER:?DEPLOY_USER is not set in .env}"
: "${DEPLOY_PATH:?DEPLOY_PATH is not set in .env}"

REMOTE="${DEPLOY_USER}@${DEPLOY_HOST}"

echo "=== Creating remote directory if needed ==="
ssh "${REMOTE}" "mkdir -p ${DEPLOY_PATH}"

echo "=== Syncing project files to ${REMOTE}:${DEPLOY_PATH} ==="
rsync -avz --delete \
  --exclude '.git' \
  --exclude '.venv' \
  --exclude 'node_modules' \
  --exclude '__pycache__' \
  --exclude '.idea' \
  --exclude '.vscode' \
  --exclude 'snapshot.json' \
  --exclude '.env' \
  ./ "${REMOTE}:${DEPLOY_PATH}"

echo "=== Copying .env to remote ==="
scp "${ENV_FILE}" "${REMOTE}:${DEPLOY_PATH}/.env"

echo "=== Building and launching containers on Raspberry Pi 5 ==="
ssh "${REMOTE}" "cd ${DEPLOY_PATH} && docker compose up -d --build backend frontend nginx ollama"

echo "=== Pulling Ollama model (qwen2.5:3b) ==="
ssh "${REMOTE}" "docker exec simple_ollama ollama pull qwen2.5:3b || true"

echo "=== Restarting voice service on Pi 5 ==="
ssh "${REMOTE}" "
  cd ${DEPLOY_PATH}/voice && \
  python3 -m venv .venv && \
  .venv/bin/pip install -q --upgrade pip && \
  .venv/bin/pip install -q openwakeword onnxruntime pyaudio numpy 'vosk==0.3.44' sounddevice httpx 'mcp<2' && \
  .venv/bin/python -c 'from openwakeword.utils import download_models; download_models()' && \
  pkill -f 'voice/main.py' 2>/dev/null || true && \
  nohup .venv/bin/python main.py > /tmp/voice.log 2>&1 &
"

echo "=== Deployment finished successfully! ==="
echo "Frontend: http://${DEPLOY_HOST}"
echo "Backend API: http://${DEPLOY_HOST}:8000"
