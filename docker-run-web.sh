#!/bin/bash
# Run NeoZen Web Docker Container

# Configuration
CONTAINER_NAME="neozen-web"
IMAGE_NAME="neozen-web:latest"
PORT="8080"

# Check if container already exists
if [ "$(docker ps -aq -f name=$CONTAINER_NAME)" ]; then
    echo "Stopping and removing existing container..."
    docker stop $CONTAINER_NAME 2>/dev/null
    docker rm $CONTAINER_NAME 2>/dev/null
fi

echo "Starting NeoZen Web container..."
docker run -d \
    --name $CONTAINER_NAME \
    -p $PORT:8080 \
    --network host \
    --cap-add=NET_ADMIN \
    --cap-add=NET_RAW \
    -v $(pwd)/scan_results:/app/scan_results \
    $IMAGE_NAME

if [ $? -eq 0 ]; then
    echo "✓ NeoZen Web is running!"
    echo ""
    echo "Access the web interface at:"
    echo "  http://localhost:$PORT"
    echo ""
    echo "To view logs:"
    echo "  docker logs -f $CONTAINER_NAME"
    echo ""
    echo "To stop:"
    echo "  docker stop $CONTAINER_NAME"
else
    echo "✗ Failed to start container"
    exit 1
fi
