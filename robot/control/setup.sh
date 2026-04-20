#!/bin/bash
# Setup Robot Environment on Raspberry Pi
# Run this once to set up the virtual environment and install dependencies

cd "$(dirname "$0")"

echo "================================"
echo "  ROVY ROBOT SETUP"
echo "================================"
echo ""

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "ERROR: Python3 not found"
    exit 1
fi

PYTHON_VERSION=$(python3 --version)
echo "Python: $PYTHON_VERSION"
echo ""

# Create virtual environment
VENV_PATH="./venv"
if [ -d "$VENV_PATH" ]; then
    echo "Virtual environment already exists at $VENV_PATH"
    read -p "Delete and recreate? (y/N) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        rm -rf "$VENV_PATH"
    else
        echo "Using existing virtual environment"
    fi
fi

if [ ! -d "$VENV_PATH" ]; then
    echo "Creating virtual environment..."
    python3 -m venv "$VENV_PATH"
    echo "✓ Virtual environment created"
fi

# Activate it
source "$VENV_PATH/bin/activate"
echo "✓ Virtual environment activated"
echo ""

# Upgrade pip
echo "Upgrading pip..."
pip install --upgrade pip
echo ""

# Install requirements
echo "Installing dependencies..."
pip install -r requirements.txt
echo ""

echo "================================"
echo "  SETUP COMPLETE!"
echo "================================"
echo ""
echo "Next steps:"
echo "1. Install systemd service:"
echo "   sudo ./install-service.sh"
echo ""
echo "2. Or run manually:"
echo "   ./start.sh"
echo ""

