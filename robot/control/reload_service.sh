#!/bin/bash
# Reload and restart the rovy service after fixes

set -e

echo "========================================"
echo "  ROVY Service Reload Script"
echo "========================================"
echo ""

# Copy service file to systemd
echo "[1/5] Copying service file to systemd..."
sudo cp /home/rovy/rovy_client/robot/rovy.service /etc/systemd/system/rovy.service

# Reload systemd daemon
echo "[2/5] Reloading systemd daemon..."
sudo systemctl daemon-reload

# Stop the service
echo "[3/5] Stopping rovy service..."
sudo systemctl stop rovy.service || true

# Wait a moment
sleep 2

# Start the service
echo "[4/5] Starting rovy service..."
sudo systemctl start rovy.service

# Check status
echo "[5/5] Checking service status..."
sleep 2
sudo systemctl status rovy.service --no-pager -l

echo ""
echo "========================================"
echo "  Service reloaded successfully!"
echo "========================================"
echo ""
echo "To view logs: journalctl -u rovy.service -f"
echo "To check status: systemctl status rovy.service"

