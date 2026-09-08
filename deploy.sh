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
rsync -avz --exclude '.git' --exclude 'node_modules' --exclude '__pycache__' --exclude 'snapshot.json' ./ "${REMOTE}:${DEPLOY_PATH}"

echo "=== Building and launching containers on target server ==="
ssh "${REMOTE}" "cd ${DEPLOY_PATH} && docker compose up -d --build"

echo "=== Deployment finished successfully! ==="
echo "Access your app at http://${DEPLOY_HOST}"
