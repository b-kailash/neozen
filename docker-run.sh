#!/bin/bash
# Run NeoZen Docker container with X11 forwarding

set -e

echo "======================================"
echo "Running NeoZen in Docker"
echo "======================================"
echo ""

# Allow X11 connections from localhost
echo "Setting up X11 forwarding..."
xhost +local:docker

# Run the container
echo "Starting NeoZen container..."
docker run -it --rm \
    --name neozen \
    --network host \
    --cap-add=NET_ADMIN \
    --cap-add=NET_RAW \
    -e DISPLAY=${DISPLAY} \
    -e QT_X11_NO_MITSHM=1 \
    -v /tmp/.X11-unix:/tmp/.X11-unix:rw \
    -v ${HOME}/.Xauthority:/home/neozen/.Xauthority:ro \
    -v $(pwd)/scans:/app/scans \
    neozen:latest

# Cleanup X11 permissions after container exits
echo ""
echo "Cleaning up..."
xhost -local:docker

echo "Container stopped."
