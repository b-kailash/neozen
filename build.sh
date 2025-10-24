#!/bin/bash
# Build script for NeoZen on Linux/macOS
# Creates a standalone executable in the project directory

set -e  # Exit on error

echo "======================================"
echo "NeoZen Build Script (Linux/macOS)"
echo "======================================"
echo ""

# Detect OS
OS="unknown"
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    OS="linux"
elif [[ "$OSTYPE" == "darwin"* ]]; then
    OS="macos"
else
    echo "❌ Unsupported operating system: $OSTYPE"
    exit 1
fi

EXEC_NAME="neozen"

echo "Detected OS: $OS"
echo ""

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Virtual environment not found. Creating one..."
    python3 -m venv venv
    echo "✓ Virtual environment created"
fi

# Activate virtual environment and install dependencies
echo "Installing dependencies..."
source venv/bin/activate
pip install --upgrade pip > /dev/null
pip install -e ".[build]" > /dev/null
echo "✓ Dependencies installed"
echo ""

# Build with PyInstaller
echo "Building executable with PyInstaller..."
pyinstaller --clean --noconfirm neozen.spec

# Move executable to project directory
echo "Moving executable to project directory..."
if [ -f "dist/neozen" ]; then
    mv dist/neozen "./neozen"
    chmod +x "./neozen"
    echo "✓ Executable created: ./neozen"
else
    echo "❌ Build failed: executable not found in dist/"
    exit 1
fi

# Clean up build artifacts
echo "Cleaning up build artifacts..."
rm -rf build/ dist/ *.spec~
echo "✓ Cleanup complete"
echo ""

# Summary
echo "======================================"
echo "✓ Build successful!"
echo "======================================"
echo ""
echo "Run the application with:"
echo "  ./neozen"
echo ""
echo "Or make it globally available:"
echo "  sudo cp neozen /usr/local/bin/neozen"
echo "  sudo chmod +x /usr/local/bin/neozen"
echo ""
