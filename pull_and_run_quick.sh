#!/bin/bash

# Quick version: Pull and run with minimal prompts
# Usage: TAG=0.0.1 PORT=8001 ./pull_and_run_quick.sh

set -e

# Configuration
REGISTRY="crpi-lp1jelcmhkef5y0u.cn-qingdao.personal.cr.aliyuncs.com"
IMAGE_NAME="aihehuo/bp-generation-api"
TAG="${TAG:-latest}"
FULL_IMAGE="$REGISTRY/$IMAGE_NAME:$TAG"

# Container configuration
CONTAINER_NAME="${CONTAINER_NAME:-bp-generation-api-remote}"
PORT="${PORT:-8000}"
OUTPUT_DIR="${OUTPUT_DIR:-./reports}"
SESSIONS_DIR="${SESSIONS_DIR:-./sessions}"

# Login (use cached credentials if available)
echo "🔐 Authenticating with registry..."
echo "${ALIYUN_DOCKER_PASSWORD:-}" | docker login --username "yc@foundertime.com" --password-stdin "$REGISTRY" 2>/dev/null || {
    if [ -z "$ALIYUN_DOCKER_PASSWORD" ]; then
        echo "❌ Error: ALIYUN_DOCKER_PASSWORD not set"
        exit 1
    fi
}

# Stop existing container
docker stop "$CONTAINER_NAME" 2>/dev/null && docker rm "$CONTAINER_NAME" 2>/dev/null || true

# Pull image
echo "📥 Pulling $FULL_IMAGE..."
docker pull "$FULL_IMAGE"

# Prepare environment from .docker.env
ENV_ARGS=()
if [ -f ".docker.env" ]; then
    while IFS='=' read -r key value; do
        [[ -z "$key" || "$key" =~ ^# ]] && continue
        value=$(echo "$value" | sed -e 's/^"//' -e 's/"$//' -e "s/^'//" -e "s/'$//")
        ENV_ARGS+=("-e" "$key=$value")
    done < ".docker.env"
fi

# Detect host gateway IP for host.docker.internal
# We want the Docker bridge gateway IP (docker0), not the system default gateway
HOST_GATEWAY_IP="172.17.0.1"  # Default Docker bridge IP

if [[ "$OSTYPE" == "darwin"* ]]; then
    HOST_GATEWAY_IP="host-gateway"
elif command -v ip >/dev/null 2>&1; then
    # Try to get Docker bridge IP from docker0 interface
    DOCKER_BRIDGE_IP=$(ip addr show docker0 2>/dev/null | grep 'inet ' | awk '{print $2}' | cut -d/ -f1)
    [ -n "$DOCKER_BRIDGE_IP" ] && HOST_GATEWAY_IP="$DOCKER_BRIDGE_IP"
fi

# Run container
echo "🚀 Starting container..."
docker run -d \
    --name "$CONTAINER_NAME" \
    -p "$PORT:8000" \
    -v "$(pwd)/$OUTPUT_DIR:/app/reports" \
    -v "$(pwd)/$SESSIONS_DIR:/tmp/bp_agent_sessions" \
    --add-host=host.docker.internal:$HOST_GATEWAY_IP \
    "${ENV_ARGS[@]}" \
    --restart unless-stopped \
    "$FULL_IMAGE"

echo "✅ Container started: http://localhost:$PORT/docs"
echo "📋 Logs: docker logs -f $CONTAINER_NAME"

