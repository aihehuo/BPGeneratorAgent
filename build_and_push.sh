#!/bin/bash

# Build and push Docker image for Vector Database API
# This script builds the Docker image and pushes it to Aliyun Container Registry

set -e

# Configuration
REGISTRY="crpi-lp1jelcmhkef5y0u.cn-qingdao.personal.cr.aliyuncs.com"
IMAGE_NAME="aihehuo/bp-generation-api"
TAG="0.0.3"  # Add tokenizer endpoint
USERNAME="yc@foundertime.com"

# Check if ALIYUN_DOCKER_PASSWORD is set
if [ -z "$ALIYUN_DOCKER_PASSWORD" ]; then
    echo "❌ Error: ALIYUN_DOCKER_PASSWORD environment variable is not set"
    echo "Please set it with: export ALIYUN_DOCKER_PASSWORD='your-password'"
    exit 1
fi

echo "🚀 Building and pushing Vector Database API Docker image"
echo "📦 Registry: $REGISTRY"
echo "🏷️  Image: $IMAGE_NAME:$TAG"

# Login to registry
echo "🔐 Logging into Aliyun Docker registry..."
echo "$ALIYUN_DOCKER_PASSWORD" | docker login --username "$USERNAME" --password-stdin "$REGISTRY"

# Build the image
echo "🔨 Building Docker image..."
docker build -t "$IMAGE_NAME:$TAG" .
docker build -t "$IMAGE_NAME:latest" .

# Tag for registry
FULL_IMAGE="$REGISTRY/$IMAGE_NAME:$TAG"
FULL_IMAGE_LATEST="$REGISTRY/$IMAGE_NAME:latest"

echo "🏷️  Tagging images..."
docker tag "$IMAGE_NAME:$TAG" "$FULL_IMAGE"
docker tag "$IMAGE_NAME:latest" "$FULL_IMAGE_LATEST"

# Push to registry
echo "📤 Pushing to registry..."
docker push "$FULL_IMAGE"
docker push "$FULL_IMAGE_LATEST"

echo "✅ Successfully built and pushed:"
echo "   - $FULL_IMAGE"
echo "   - $FULL_IMAGE_LATEST"
echo ""
echo "🔄 To pull and run locally, use:"
echo "   ./pull_and_run.sh"
echo "   # or specify a tag:"
echo "   TAG=$TAG ./pull_and_run.sh" 