#!/bin/bash
# Build NeoZen Docker container

set -e

echo "======================================"
echo "Building NeoZen Docker Container"
echo "======================================"
echo ""

# Build the Docker image
echo "Building image..."
docker build -t neozen:latest .

# Check the image size
echo ""
echo "======================================"
echo "Build Complete!"
echo "======================================"
echo ""
docker images neozen:latest
echo ""
echo "To run the container:"
echo "  ./docker-run.sh"
echo ""
echo "Or use docker-compose:"
echo "  docker-compose up"
echo ""
