#!/bin/bash

# Deploy BP Generation API Docker container to remote prod2 server
# This script SSHs into prod2, pulls the Docker image, and runs it

set -e

# Configuration - should match build_and_push.sh
REGISTRY="crpi-lp1jelcmhkef5y0u.cn-qingdao.personal.cr.aliyuncs.com"
IMAGE_NAME="aihehuo/bp-generation-api"
TAG="${TAG:-latest}"  # Default to latest, can be overridden with TAG=0.0.1 ./deploy_to_prod2.sh
FULL_IMAGE="$REGISTRY/$IMAGE_NAME:$TAG"

# Remote server configuration
REMOTE_HOST="${REMOTE_HOST:-prod2}"
REMOTE_USER="${REMOTE_USER:-root}"
REMOTE_DIR="/mnt/bp-generation-api"
CONTAINER_NAME="bp-generation-api"
PORT="${PORT:-8000}"

# Check if ALIYUN_DOCKER_PASSWORD is set
if [ -z "$ALIYUN_DOCKER_PASSWORD" ]; then
    echo "❌ Error: ALIYUN_DOCKER_PASSWORD environment variable is not set"
    echo "Please set it with: export ALIYUN_DOCKER_PASSWORD='your-password'"
    exit 1
fi

# Check if .docker.env exists locally
ENV_FILE=".docker.env"
if [ ! -f "$ENV_FILE" ]; then
    echo "❌ Error: $ENV_FILE not found"
    echo "Please create $ENV_FILE with your API keys before deploying"
    exit 1
fi

echo "🚀 Deploying BP Generation API to $REMOTE_USER@$REMOTE_HOST"
echo "📦 Image: $FULL_IMAGE"
echo "📁 Remote directory: $REMOTE_DIR"
echo "🌐 Port: $PORT"
echo ""

# Create remote directory structure
echo "📁 Creating remote directory structure..."
ssh "$REMOTE_USER@$REMOTE_HOST" "mkdir -p $REMOTE_DIR/reports $REMOTE_DIR/sessions"

# Read environment variables from local .docker.env file and prepare for docker run
echo "📋 Loading environment variables from local .docker.env file..."
DOCKER_ENV_FILE_CONTENT=""
while IFS='=' read -r key value; do
    # Skip empty lines and comments
    [[ -z "$key" || "$key" =~ ^# ]] && continue
    # Remove quotes from value if present
    value=$(echo "$value" | sed -e 's/^"//' -e 's/"$//' -e "s/^'//" -e "s/'$//")
    # Add to env file content (for temporary file)
    DOCKER_ENV_FILE_CONTENT+="$key=$value"$'\n'
done < "$ENV_FILE"
# Add OUTPUT_DIR override
DOCKER_ENV_FILE_CONTENT+="OUTPUT_DIR=/app/reports"$'\n'

# Execute deployment commands on remote server
echo "🚀 Executing deployment on remote server..."
ssh "$REMOTE_USER@$REMOTE_HOST" bash <<REMOTE_SCRIPT_END
set -e

REGISTRY="$REGISTRY"
FULL_IMAGE="$FULL_IMAGE"
CONTAINER_NAME="$CONTAINER_NAME"
PORT="$PORT"
REMOTE_DIR="$REMOTE_DIR"
ALIYUN_DOCKER_PASSWORD="$ALIYUN_DOCKER_PASSWORD"

echo "📥 Logging into Docker registry..."
echo "\$ALIYUN_DOCKER_PASSWORD" | docker login --username "yc@foundertime.com" --password-stdin "\$REGISTRY"

echo "📁 Setting up directories..."
mkdir -p "\$REMOTE_DIR/reports"
mkdir -p "\$REMOTE_DIR/sessions"

echo "📥 Pulling Docker image: \$FULL_IMAGE"
docker pull "\$FULL_IMAGE"

# Stop and remove existing container if it exists
if [ "\$(docker ps -a -q -f name=\$CONTAINER_NAME)" ]; then
    echo "🛑 Stopping existing container: \$CONTAINER_NAME"
    docker stop \$CONTAINER_NAME > /dev/null 2>&1 || true
    echo "🗑️  Removing existing container: \$CONTAINER_NAME"
    docker rm \$CONTAINER_NAME > /dev/null 2>&1 || true
fi

# Create temporary env file on remote server
ENV_FILE_TMP="\$REMOTE_DIR/.docker.env.tmp"
cat > "\$ENV_FILE_TMP" <<ENVEOF
$(echo -n "$DOCKER_ENV_FILE_CONTENT")
ENVEOF

echo "🚀 Starting container: \$CONTAINER_NAME"
docker run -d \\
    --name "\$CONTAINER_NAME" \\
    -p "\$PORT:8000" \\
    -v "\$REMOTE_DIR/reports:/app/reports" \\
    -v "\$REMOTE_DIR/sessions:/tmp/bp_agent_sessions" \\
    --env-file "\$ENV_FILE_TMP" \\
    --restart unless-stopped \\
    "\$FULL_IMAGE"

# Clean up temporary env file
rm -f "\$ENV_FILE_TMP"

# Wait a moment for container to start
sleep 3

# Check if container is running
if [ "\$(docker ps -q -f name=\$CONTAINER_NAME)" ]; then
    echo "✅ Container is running!"
    echo ""
    echo "📊 Container status:"
    docker ps -f name=\$CONTAINER_NAME
    echo ""
    echo "📝 Container logs (last 20 lines):"
    docker logs --tail=20 "\$CONTAINER_NAME"
else
    echo "❌ Container failed to start. Check logs with:"
    echo "   docker logs \$CONTAINER_NAME"
    exit 1
fi
REMOTE_SCRIPT_END

echo ""
echo "✅ Deployment completed!"
echo ""
echo "🔗 Access the API at:"
echo "   - API Docs: http://$REMOTE_HOST:$PORT/docs"
echo "   - Health Check: http://$REMOTE_HOST:$PORT/health"
echo ""
echo "📋 Useful remote commands:"
echo "   ssh $REMOTE_USER@$REMOTE_HOST 'docker logs -f $CONTAINER_NAME'"
echo "   ssh $REMOTE_USER@$REMOTE_HOST 'docker stop $CONTAINER_NAME'"
echo "   ssh $REMOTE_USER@$REMOTE_HOST 'docker restart $CONTAINER_NAME'"
echo "   ssh $REMOTE_USER@$REMOTE_HOST 'docker ps -f name=$CONTAINER_NAME'"

