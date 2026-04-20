#!/bin/bash
# Install ROVY as a systemd service (runs on boot)

echo "Installing ROVY service..."

# Copy service file
sudo cp rovy.service /etc/systemd/system/

# Reload systemd
sudo systemctl daemon-reload

# Enable service (start on boot)
sudo systemctl enable rovy.service

echo ""
echo "✓ ROVY service installed!"
echo ""
echo "Commands:"
echo "  sudo systemctl start rovy    - Start now"
echo "  sudo systemctl stop rovy     - Stop"
echo "  sudo systemctl restart rovy  - Restart"
echo "  sudo systemctl status rovy   - Check status"
echo "  journalctl -u rovy -f        - View logs"
echo ""
echo "The service will start automatically on boot."

