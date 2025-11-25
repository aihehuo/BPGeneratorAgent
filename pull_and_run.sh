#!/bin/bash

# Pull and run BP Generation API Docker image from remote registry
# This script pulls the Docker image from Aliyun Container Registry and runs it locally

set -e

# Configuration - should match build_and_push.sh
REGISTRY="crpi-lp1jelcmhkef5y0u.cn-qingdao.personal.cr.aliyuncs.com"
IMAGE_NAME="aihehuo/bp-generation-api"
TAG="${TAG:-latest}"  # Default to latest, can be overridden with TAG=0.0.1 ./pull_and_run.sh
FULL_IMAGE="$REGISTRY/$IMAGE_NAME:$TAG"

# Container configuration
CONTAINER_NAME="bp-generation-api-remote"
PORT="${PORT:-8001}"
OUTPUT_DIR="${OUTPUT_DIR:-./reports}"
SESSIONS_DIR="${SESSIONS_DIR:-./sessions}"

# Check if ALIYUN_DOCKER_PASSWORD is set
if [ -z "$ALIYUN_DOCKER_PASSWORD" ]; then
    echo "❌ Error: ALIYUN_DOCKER_PASSWORD environment variable is not set"
    echo "Please set it with: export ALIYUN_DOCKER_PASSWORD='your-password'"
    exit 1
fi

# Check if .docker.env exists
ENV_FILE=".docker.env"
if [ ! -f "$ENV_FILE" ]; then
    echo "⚠️  Warning: $ENV_FILE not found"
    echo "Creating from template..."
    if [ -f ".docker.env.example" ]; then
        cp .docker.env.example .docker.env
        echo "✅ Created $ENV_FILE from template"
        echo "⚠️  Please edit $ENV_FILE and add your API keys before continuing"
        read -p "Press Enter to continue after editing $ENV_FILE, or Ctrl+C to cancel..."
    else
        echo "❌ Error: Neither $ENV_FILE nor .docker.env.example found"
        echo "Please create $ENV_FILE with your API keys"
        exit 1
    fi
fi

# Login to registry
echo "🔐 Logging into Aliyun Docker registry..."
echo "$ALIYUN_DOCKER_PASSWORD" | docker login --username "yc@foundertime.com" --password-stdin "$REGISTRY"

# Stop and remove existing container if it exists
if [ "$(docker ps -a -q -f name=$CONTAINER_NAME)" ]; then
    echo "🛑 Stopping existing container: $CONTAINER_NAME"
    docker stop $CONTAINER_NAME > /dev/null 2>&1 || true
    echo "🗑️  Removing existing container: $CONTAINER_NAME"
    docker rm $CONTAINER_NAME > /dev/null 2>&1 || true
fi

# Pull the image
echo "📥 Pulling Docker image: $FULL_IMAGE"
docker pull "$FULL_IMAGE"

# Create necessary directories
mkdir -p "$OUTPUT_DIR"
mkdir -p "$SESSIONS_DIR"

# Prepare environment variables from .docker.env file
ENV_ARGS=()
while IFS='=' read -r key value; do
    # Skip empty lines and comments
    [[ -z "$key" || "$key" =~ ^# ]] && continue
    # Remove quotes from value if present
    value=$(echo "$value" | sed -e 's/^"//' -e 's/"$//' -e "s/^'//" -e "s/'$//")
    ENV_ARGS+=("-e" "$key=$value")
done < "$ENV_FILE"

# Override OUTPUT_DIR in container
ENV_ARGS+=("-e" "OUTPUT_DIR=/app/reports")

# Run the container
echo "🚀 Starting container: $CONTAINER_NAME"
echo "📦 Image: $FULL_IMAGE"
echo "🌐 Port: $PORT"
echo "📁 Reports: $OUTPUT_DIR"
echo "📁 Sessions: $SESSIONS_DIR"
echo ""

docker run -d \
    --name "$CONTAINER_NAME" \
    -p "$PORT:8000" \
    -v "$(pwd)/$OUTPUT_DIR:/app/reports" \
    -v "$(pwd)/$SESSIONS_DIR:/tmp/bp_agent_sessions" \
    "${ENV_ARGS[@]}" \
    --restart unless-stopped \
    "$FULL_IMAGE"

# Wait a moment for container to start
echo ""
echo "⏳ Waiting for container to start..."
sleep 3

# Check if container is running
if [ "$(docker ps -q -f name=$CONTAINER_NAME)" ]; then
    echo "✅ Container is running!"
    echo ""
    echo "📊 Container status:"
    docker ps -f name=$CONTAINER_NAME
    echo ""
    echo "📝 Container logs (last 20 lines):"
    docker logs --tail=20 "$CONTAINER_NAME"
    echo ""
    echo "🔗 Access the API at:"
    echo "   - API Docs: http://localhost:$PORT/docs"
    echo "   - Health Check: http://localhost:$PORT/health"
    echo "   - Root: http://localhost:$PORT/"
    echo ""
    echo "📋 Useful commands:"
    echo "   - View logs: docker logs -f $CONTAINER_NAME"
    echo "   - Stop: docker stop $CONTAINER_NAME"
    echo "   - Remove: docker rm $CONTAINER_NAME"
    echo "   - Restart: docker restart $CONTAINER_NAME"
else
    echo "❌ Container failed to start. Check logs with:"
    echo "   docker logs $CONTAINER_NAME"
    exit 1
fi

