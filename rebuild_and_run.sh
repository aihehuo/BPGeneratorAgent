#!/bin/bash
# Rebuild and run the Docker container

echo "Stopping existing container..."
docker-compose down

echo "Rebuilding container with updated code..."
docker-compose build #--no-cache

echo "Starting container..."
docker-compose up -d

echo "Waiting for container to start..."
sleep 5

echo "Checking container logs..."
docker-compose logs --tail=50

echo ""
echo "Container should now be running. Check logs above for any errors."
echo "To view logs in real-time: docker-compose logs -f"
echo "To check health: curl http://localhost:8000/health"

