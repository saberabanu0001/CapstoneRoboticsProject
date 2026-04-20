#!/bin/bash
# Disable WirePlumber/PipeWire to prevent conflicts with PyAudio ALSA access
# This must run before the robot service starts

echo "[Audio Fix] Disabling WirePlumber/PipeWire for robot user..."

# Stop and mask the services
systemctl --user stop wireplumber pipewire pipewire-pulse 2>/dev/null
systemctl --user mask wireplumber pipewire pipewire-pulse 2>/dev/null

# Kill any lingering processes
killall -9 wireplumber pipewire pipewire-pulse 2>/dev/null

# Disable the sockets that auto-restart them
systemctl --user mask pipewire.socket pipewire-pulse.socket 2>/dev/null

echo "[Audio Fix] ✓ WirePlumber/PipeWire disabled"

