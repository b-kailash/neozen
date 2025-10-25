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
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Check for root/sudo privileges
echo "🔐 Checking privileges..."
if [ "$EUID" -eq 0 ]; then
    echo -e "${RED}❌ Please do not run this script as root.${NC}"
    echo "This script will use sudo when needed for system package installation."
    echo "Please run as a regular user: ./install.sh"
    exit 1
fi

# Check if user has sudo access
if ! sudo -v &> /dev/null; then
    echo -e "${RED}❌ This script requires sudo privileges for system package installation.${NC}"
    echo "Please ensure your user has sudo access or is in the sudoers file."
    exit 1
fi

echo -e "${GREEN}✓ Running with proper privileges (user with sudo access)${NC}"
echo ""

# Check for Python
echo "🔍 Checking for Python 3..."
echo -e "${BLUE}Running: python3 --version${NC}"
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}❌ Python 3 not found.${NC}"
    echo "Please install Python 3.7 or higher:"
    echo "  • Ubuntu/Debian: sudo apt install python3 python3-venv python3-pip"
    echo "  • Fedora/RHEL: sudo dnf install python3 python3-pip"
    echo "  • macOS: brew install python3"
    exit 1
fi

PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
PYTHON_PATH=$(which python3)
echo -e "${GREEN}✓ Found Python $PYTHON_VERSION${NC}"
echo -e "${BLUE}  Location: $PYTHON_PATH${NC}"

# Check for Nmap
echo ""
echo "🔍 Checking for Nmap..."
echo -e "${BLUE}Running: nmap --version${NC}"
if ! command -v nmap &> /dev/null; then
    echo -e "${YELLOW}⚠️  Nmap not found. Attempting to install...${NC}"

    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        # Linux installation
        if command -v apt-get &> /dev/null; then
            echo -e "${BLUE}Installing Nmap using apt...${NC}"
            echo -e "${BLUE}Running: sudo apt-get update && sudo apt-get install -y nmap${NC}"
            sudo apt-get update && sudo apt-get install -y nmap
        elif command -v dnf &> /dev/null; then
            echo -e "${BLUE}Installing Nmap using dnf...${NC}"
            echo -e "${BLUE}Running: sudo dnf install -y nmap${NC}"
            sudo dnf install -y nmap
        elif command -v yum &> /dev/null; then
            echo -e "${BLUE}Installing Nmap using yum...${NC}"
            echo -e "${BLUE}Running: sudo yum install -y nmap${NC}"
            sudo yum install -y nmap
        elif command -v pacman &> /dev/null; then
            echo -e "${BLUE}Installing Nmap using pacman...${NC}"
            echo -e "${BLUE}Running: sudo pacman -S --noconfirm nmap${NC}"
            sudo pacman -S --noconfirm nmap
        else
            echo -e "${RED}❌ Could not find a package manager to install Nmap.${NC}"
            echo "Please install Nmap manually and re-run this script."
            exit 1
        fi
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS installation
        if command -v brew &> /dev/null; then
            echo -e "${BLUE}Installing Nmap using Homebrew...${NC}"
            echo -e "${BLUE}Running: brew install nmap${NC}"
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
NMAP_PATH=$(which nmap)
echo -e "${GREEN}✓ Found Nmap $NMAP_VERSION${NC}"
echo -e "${BLUE}  Location: $NMAP_PATH${NC}"

# Create virtual environment
echo ""
echo "📦 Creating virtual environment..."
if [ -d "venv" ]; then
    echo -e "${YELLOW}⚠️  Virtual environment already exists. Removing...${NC}"
    echo -e "${BLUE}Running: rm -rf venv${NC}"
    rm -rf venv
fi

echo -e "${BLUE}Running: python3 -m venv venv${NC}"
python3 -m venv venv
echo -e "${GREEN}✓ Virtual environment created${NC}"
echo -e "${BLUE}  Location: $(pwd)/venv${NC}"

# Activate virtual environment
echo ""
echo "🔧 Activating virtual environment..."
echo -e "${BLUE}Running: source venv/bin/activate${NC}"
source venv/bin/activate
echo -e "${GREEN}✓ Virtual environment activated${NC}"
echo -e "${BLUE}  Python: $(which python)${NC}"

# Upgrade pip
echo ""
echo "⬆️  Upgrading pip..."
echo -e "${BLUE}Running: pip install --upgrade pip${NC}"
pip install --upgrade pip

# Install NeoZen with all dependencies (desktop + web)
echo ""
echo "📥 Installing NeoZen and dependencies (desktop + web)..."
echo -e "${BLUE}Running: pip install -e \".[all]\"${NC}"
pip install -e ".[all]"

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ NeoZen installed successfully!${NC}"
else
    echo -e "${RED}❌ Installation failed.${NC}"
    exit 1
fi

# Build standalone executable
echo ""
echo "🔨 Building standalone executable..."
echo -e "${BLUE}Running: pip install -e \".[build]\"${NC}"
pip install -e ".[build]"

if [ $? -eq 0 ]; then
    echo ""
    echo -e "${BLUE}Running: pyinstaller --clean --noconfirm neozen.spec${NC}"
    pyinstaller --clean --noconfirm neozen.spec

    # Move executable to project directory
    if [ -f "dist/neozen" ]; then
        echo ""
        echo -e "${BLUE}Moving executable to project directory...${NC}"
        echo -e "${BLUE}Running: mv dist/neozen ./neozen${NC}"
        mv dist/neozen ./neozen
        echo -e "${BLUE}Running: chmod +x ./neozen${NC}"
        chmod +x ./neozen
        echo -e "${GREEN}✓ Standalone executable created: ./neozen${NC}"
        echo -e "${BLUE}  Size: $(du -h ./neozen | cut -f1)${NC}"

        # Clean up build artifacts
        echo ""
        echo -e "${BLUE}Cleaning up build artifacts...${NC}"
        echo -e "${BLUE}Running: rm -rf build/ dist/${NC}"
        rm -rf build/ dist/
        echo -e "${GREEN}✓ Build artifacts cleaned${NC}"
    else
        echo -e "${YELLOW}⚠️  Standalone executable build failed, but virtual environment installation succeeded.${NC}"
    fi
else
    echo -e "${YELLOW}⚠️  Could not install build dependencies, but virtual environment installation succeeded.${NC}"
fi

# Installation complete
echo ""
echo "╔════════════════════════════════════════╗"
echo "║     Installation Complete! 🎉          ║"
echo "╚════════════════════════════════════════╝"
echo ""
echo -e "${BLUE}═══════════════ Installation Summary ═══════════════${NC}"
echo -e "${GREEN}✓ Python:${NC} $PYTHON_VERSION ($PYTHON_PATH)"
echo -e "${GREEN}✓ Nmap:${NC} $NMAP_VERSION ($NMAP_PATH)"
echo -e "${GREEN}✓ Virtual Environment:${NC} $(pwd)/venv"
echo -e "${GREEN}✓ NeoZen:${NC} Installed (pip show neozen for details)"
if [ -f "./neozen" ]; then
    echo -e "${GREEN}✓ Standalone Executable:${NC} ./neozen ($(du -h ./neozen | cut -f1))"
fi
echo -e "${BLUE}════════════════════════════════════════════════════${NC}"
echo ""
echo "To start NeoZen:"
echo ""
if [ -f "./neozen" ]; then
    echo -e "${GREEN}Option 1 (Recommended): Run standalone executable${NC}"
    echo -e "${GREEN}  ./neozen${NC}"
    echo ""
    echo "Option 2: Use virtual environment:"
fi
echo -e "${GREEN}  source venv/bin/activate${NC}"
echo -e "${GREEN}  neozen${NC}"
echo ""
echo "Or directly:"
echo -e "${GREEN}  ./venv/bin/neozen${NC}"
echo ""
echo "To deactivate the virtual environment later, run:"
echo "  deactivate"
echo ""
