#!/bin/bash
# Deploy the checked-in Kai app to a Linux host using the repo's real Docker assets.

set -euo pipefail

APP_ROOT="/opt/kai-enterprise"
SOURCE_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TARGET_ROOT="$APP_ROOT/app"

echo "========================================"
echo "KAI ENTERPRISE - CLOUD DEPLOYMENT"
echo "========================================"
echo ""

if [[ $EUID -ne 0 ]]; then
  echo "This script must be run as root"
  exit 1
fi

if [[ ! -f "$SOURCE_ROOT/docker-compose-enterprise.yml" || ! -f "$SOURCE_ROOT/Dockerfile" ]]; then
  echo "Expected to run from the Kai repo. Missing docker-compose-enterprise.yml or Dockerfile."
  exit 1
fi

install_if_missing() {
  local cmd="$1"
  shift
  if ! command -v "$cmd" >/dev/null 2>&1; then
    "$@"
  fi
}

echo "[1/6] Installing system packages..."
apt-get update
apt-get install -y curl git rsync ca-certificates

echo "[2/6] Ensuring Docker is installed..."
install_if_missing docker bash -lc 'curl -fsSL https://get.docker.com | sh'
systemctl enable docker
systemctl start docker

echo "[3/6] Ensuring Docker Compose plugin is available..."
if ! docker compose version >/dev/null 2>&1; then
  apt-get install -y docker-compose-plugin
fi

echo "[4/6] Syncing checked-in repo files..."
mkdir -p "$TARGET_ROOT"
rsync -a --delete \
  --exclude ".git" \
  --exclude ".venv" \
  --exclude "__pycache__" \
  --exclude "*.pyc" \
  --exclude ".kai" \
  --exclude "tmp" \
  --exclude "logs" \
  --exclude "downloads" \
  --exclude "documents" \
  "$SOURCE_ROOT"/ "$TARGET_ROOT"/

mkdir -p "$TARGET_ROOT/kai_data" "$TARGET_ROOT/projects"

echo "[5/6] Building and starting Kai from checked-in Docker assets..."
cd "$TARGET_ROOT"
docker compose -f docker-compose-enterprise.yml up -d --build

echo "[6/6] Current container status:"
docker compose -f docker-compose-enterprise.yml ps

HOST_IP="$(hostname -I | awk '{print $1}')"
if [[ -z "$HOST_IP" ]]; then
  HOST_IP="localhost"
fi

echo ""
echo "Deployment complete."
echo "API: http://$HOST_IP:8001/"
echo "Docs: http://$HOST_IP:8001/docs"
echo ""
echo "Environment notes:"
echo "- Edit $TARGET_ROOT/docker-compose-enterprise.yml to choose Ollama vs other backends."
echo "- This script deploys the checked-in repo files only; it no longer embeds stale app copies."
