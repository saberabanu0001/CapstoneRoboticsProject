#!/bin/bash
# Fix USB audio power management issues that cause timeouts

echo "[USB Audio Fix] Disabling USB autosuspend for audio devices..."

# Disable USB autosuspend for all USB audio devices
for device in /sys/bus/usb/devices/*/idProduct; do
    dir=$(dirname "$device")
    
    # Check if this is an audio device (class 01 = audio)
    if [ -f "$dir/bInterfaceClass" ]; then
        class=$(cat "$dir/bInterfaceClass" 2>/dev/null)
        if [ "$class" = "01" ]; then
            # Disable autosuspend
            echo "on" | sudo tee "$dir/power/control" > /dev/null 2>&1
            echo "[USB Audio Fix] Disabled autosuspend for device in $dir"
        fi
    fi
    
    # Also check parent device
    if [ -f "$dir/bDeviceClass" ]; then
        class=$(cat "$dir/bDeviceClass" 2>/dev/null)
        if [ "$class" = "00" ] || [ "$class" = "01" ]; then
            # Composite or audio device
            echo "on" | sudo tee "$dir/power/control" > /dev/null 2>&1
        fi
    fi
done

# Specifically target known USB audio cards
for card in /sys/class/sound/card*/device; do
    if [ -L "$card" ]; then
        real_path=$(readlink -f "$card")
        if [[ "$real_path" == *"usb"* ]]; then
            # Find the USB device directory
            usb_dir=$(echo "$real_path" | grep -o '/sys/bus/usb/devices/[^/]*' | head -1)
            if [ -n "$usb_dir" ] && [ -f "$usb_dir/power/control" ]; then
                echo "on" | sudo tee "$usb_dir/power/control" > /dev/null 2>&1
                echo "[USB Audio Fix] Disabled autosuspend for USB audio card: $(basename $card)"
            fi
        fi
    fi
done

echo "[USB Audio Fix] ✓ USB power management configured"

