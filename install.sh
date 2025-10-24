#!/bin/bash
# NeoZen Installation Script for Linux and macOS
# This script sets up a virtual environment and installs NeoZen with all dependencies

set -e  # Exit on any error

echo "╔════════════════════════════════════════╗"
echo "║   NeoZen - Modern Nmap GUI Installer   ║"
echo "╚════════════════════════════════════════╝"
echo ""

# Color codes for better output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check for Python
echo "🔍 Checking for Python 3..."
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}❌ Python 3 not found.${NC}"
    echo "Please install Python 3.7 or higher:"
    echo "  • Ubuntu/Debian: sudo apt install python3 python3-venv python3-pip"
    echo "  • Fedora/RHEL: sudo dnf install python3 python3-pip"
    echo "  • macOS: brew install python3"
    exit 1
fi

PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
echo -e "${GREEN}✓ Found Python $PYTHON_VERSION${NC}"

# Check for Nmap
echo ""
echo "🔍 Checking for Nmap..."
if ! command -v nmap &> /dev/null; then
    echo -e "${YELLOW}⚠️  Nmap not found. Attempting to install...${NC}"

    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        # Linux installation
        if command -v apt-get &> /dev/null; then
            echo "Installing Nmap using apt..."
            sudo apt-get update && sudo apt-get install -y nmap
        elif command -v dnf &> /dev/null; then
            echo "Installing Nmap using dnf..."
            sudo dnf install -y nmap
        elif command -v yum &> /dev/null; then
            echo "Installing Nmap using yum..."
            sudo yum install -y nmap
        elif command -v pacman &> /dev/null; then
            echo "Installing Nmap using pacman..."
            sudo pacman -S --noconfirm nmap
        else
            echo -e "${RED}❌ Could not find a package manager to install Nmap.${NC}"
            echo "Please install Nmap manually and re-run this script."
            exit 1
        fi
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS installation
        if command -v brew &> /dev/null; then
            echo "Installing Nmap using Homebrew..."
            brew install nmap
        else
            echo -e "${RED}❌ Homebrew not found.${NC}"
            echo "Please install Homebrew from https://brew.sh/ or install Nmap manually."
            exit 1
        fi
    else
        echo -e "${RED}❌ Unsupported operating system.${NC}"
        echo "Please install Nmap manually from https://nmap.org"
        exit 1
    fi

    # Verify installation
    if ! command -v nmap &> /dev/null; then
        echo -e "${RED}❌ Nmap installation failed.${NC}"
        exit 1
    fi
fi

NMAP_VERSION=$(nmap --version 2>&1 | head -n1 | awk '{print $3}')
echo -e "${GREEN}✓ Found Nmap $NMAP_VERSION${NC}"

# Create virtual environment
echo ""
echo "📦 Creating virtual environment..."
if [ -d "venv" ]; then
    echo -e "${YELLOW}⚠️  Virtual environment already exists. Removing...${NC}"
    rm -rf venv
fi

python3 -m venv venv
echo -e "${GREEN}✓ Virtual environment created${NC}"

# Activate virtual environment
echo ""
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo ""
echo "⬆️  Upgrading pip..."
pip install --upgrade pip --quiet

# Install NeoZen
echo ""
echo "📥 Installing NeoZen and dependencies..."
pip install -e . --quiet

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ NeoZen installed successfully!${NC}"
else
    echo -e "${RED}❌ Installation failed.${NC}"
    exit 1
fi

# Installation complete
echo ""
echo "╔════════════════════════════════════════╗"
echo "║     Installation Complete! 🎉          ║"
echo "╚════════════════════════════════════════╝"
echo ""
echo "To start NeoZen, run:"
echo -e "${GREEN}  source venv/bin/activate${NC}"
echo -e "${GREEN}  neozen${NC}"
echo ""
echo "Or simply:"
echo -e "${GREEN}  ./venv/bin/neozen${NC}"
echo ""
echo "To deactivate the virtual environment later, run:"
echo "  deactivate"
echo ""
