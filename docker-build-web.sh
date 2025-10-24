#!/bin/bash
# Build NeoZen Web Docker Image

echo "Building NeoZen Web Docker image..."
docker build -f Dockerfile.web -t neozen-web:latest .

if [ $? -eq 0 ]; then
    echo "✓ Docker image built successfully: neozen-web:latest"
    echo ""
    echo "To run the web interface:"
    echo "  ./docker-run-web.sh"
    echo ""
    echo "Or manually:"
    echo "  docker run -d -p 8080:8080 --name neozen-web neozen-web:latest"
else
    echo "✗ Failed to build Docker image"
    exit 1
fi
