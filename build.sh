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
    EXEC_NAME="neozen-linux"
elif [[ "$OSTYPE" == "darwin"* ]]; then
    OS="macos"
    EXEC_NAME="neozen-macos"
else
    echo "❌ Unsupported operating system: $OSTYPE"
    exit 1
fi

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
    mv dist/neozen "./$EXEC_NAME"
    chmod +x "./$EXEC_NAME"
    echo "✓ Executable created: ./$EXEC_NAME"
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
echo "  ./$EXEC_NAME"
echo ""
echo "Or make it globally available:"
echo "  sudo cp $EXEC_NAME /usr/local/bin/neozen"
echo "  sudo chmod +x /usr/local/bin/neozen"
echo ""
