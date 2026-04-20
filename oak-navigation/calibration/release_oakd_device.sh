#!/bin/bash
# Force release OAK-D device if stuck in use
# Run this if you get X_LINK_DEVICE_ALREADY_IN_USE errors

echo "🔧 OAK-D Device Release Tool"
echo "================================"
echo ""

# Kill any processes using the OAK-D device
echo "[1] Checking for processes using OAK-D..."
PROCS=$(ps aux | grep -E "python.*main_api|python.*navigation|python.*oakd" | grep -v grep | awk '{print $2}')

if [ -z "$PROCS" ]; then
    echo "  ✓ No OAK-D processes found"
else
    echo "  Found processes: $PROCS"
    for PID in $PROCS; do
        echo "    Killing PID $PID..."
        kill -9 $PID 2>/dev/null || true
    done
    sleep 1
    echo "  ✓ Processes terminated"
fi

# Reset USB devices (requires root)
echo ""
echo "[2] Resetting USB devices..."
if [ "$EUID" -eq 0 ]; then
    # Find OAK-D USB devices (Luxonis/Movidius)
    for DEV in /sys/bus/usb/devices/*/idVendor; do
        VENDOR=$(cat "$DEV" 2>/dev/null)
        if [ "$VENDOR" = "03e7" ]; then  # Luxonis vendor ID
            DEV_PATH=$(dirname "$DEV")
            DEV_NAME=$(basename "$DEV_PATH")
            echo "  Found OAK-D device: $DEV_NAME"
            echo "    Unbinding..."
            echo "$DEV_NAME" > /sys/bus/usb/drivers/usb/unbind 2>/dev/null || true
            sleep 0.5
            echo "    Rebinding..."
            echo "$DEV_NAME" > /sys/bus/usb/drivers/usb/bind 2>/dev/null || true
            echo "  ✓ Device reset"
        fi
    done
else
    echo "  ⚠️  Not running as root, skipping USB reset"
    echo "     Run with sudo for full reset: sudo $0"
fi

echo ""
echo "[3] Cleanup complete!"
echo ""
echo "You can now try starting navigation again."
echo ""

