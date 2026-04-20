#!/bin/bash
# Start Rovy Robot
# 1. WiFi Provisioning (if no WiFi) - creates hotspot for phone setup
# 2. Main API server

cd "$(dirname "$0")"

echo "================================"
echo "  ROVY ROBOT STARTUP"
echo "================================"

# Activate virtual environment (robot-specific)
VENV_PATH="/home/rovy/rovy_client/robot/venv"
if [ -d "$VENV_PATH" ]; then
    source "$VENV_PATH/bin/activate"
    echo "✓ Virtual environment activated"
else
    echo "WARNING: Virtual environment not found at $VENV_PATH"
    echo "Create it with: python3 -m venv /home/rovy/rovy_client/robot/venv"
    echo "                pip install -r /home/rovy/rovy_client/robot/requirements.txt"
fi

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "ERROR: Python3 not found"
    exit 1
fi

# Step 1: WiFi Provisioning (Hotspot if no WiFi)
echo ""
echo "[1/2] Checking WiFi connection..."

# Check if connected to WiFi
WIFI_CONNECTED=$(nmcli -t -f TYPE,STATE device status | grep "wifi:connected" || true)

if [ -z "$WIFI_CONNECTED" ]; then
    echo "No WiFi connection detected."
    echo "Starting WiFi provisioning (hotspot mode)..."
    echo ""
    python3 wifi_provision.py
    
    # Re-check after provisioning
    WIFI_CONNECTED=$(nmcli -t -f TYPE,STATE device status | grep "wifi:connected" || true)
    if [ -z "$WIFI_CONNECTED" ]; then
        echo "ERROR: WiFi still not connected after provisioning"
        exit 1
    fi
else
    echo "✓ WiFi already connected"
fi

# Show current IP
IP=$(hostname -I | awk '{print $1}')
echo "✓ IP Address: $IP"
echo ""

# Step 2: Start robot server with API
echo "[2/2] Starting robot server with API..."
echo ""
# Stay in robot directory and run robot server using venv's python
if [ -f "$VENV_PATH/bin/python" ]; then
    "$VENV_PATH/bin/python" main_api.py
else
    # Fallback to system python if venv not found
    python3 main_api.py
fi
