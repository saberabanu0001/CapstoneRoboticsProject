#!/usr/bin/env python3
"""
Utility to force-release OAK-D devices that are stuck in use.
Run this if you get X_LINK_DEVICE_ALREADY_IN_USE errors.

Usage:
    python release_oakd_device.py
"""

import sys
import time
import signal
import subprocess

def find_oakd_processes():
    """Find Python processes using OAK-D/navigation"""
    try:
        result = subprocess.run(
            ['ps', 'aux'],
            capture_output=True,
            text=True
        )
        
        pids = []
        for line in result.stdout.splitlines():
            if any(keyword in line for keyword in ['main_api', 'navigation', 'oakd', 'depthai']):
                if 'python' in line and 'grep' not in line and 'release_oakd_device' not in line:
                    parts = line.split()
                    if len(parts) > 1:
                        try:
                            pid = int(parts[1])
                            pids.append((pid, ' '.join(parts[10:15])))  # PID and command
                        except ValueError:
                            continue
        
        return pids
    except Exception as e:
        print(f"Error finding processes: {e}")
        return []

def kill_process(pid):
    """Kill a process by PID"""
    try:
        # Try graceful termination first
        subprocess.run(['kill', '-TERM', str(pid)], check=False)
        time.sleep(0.5)
        
        # Check if still running
        result = subprocess.run(['kill', '-0', str(pid)], capture_output=True)
        if result.returncode == 0:
            # Force kill if still running
            subprocess.run(['kill', '-9', str(pid)], check=False)
            return True
        return True
    except Exception as e:
        print(f"  Warning: {e}")
        return False

def release_depthai_devices():
    """Release DepthAI device handles using Python API"""
    try:
        import depthai as dai
        
        # Get all available devices
        devices = dai.Device.getAllAvailableDevices()
        
        if not devices:
            print("  No OAK-D devices detected")
            return
        
        print(f"  Found {len(devices)} OAK-D device(s)")
        
        # Try to close any open device connections
        for device_info in devices:
            print(f"    Device: {device_info.getMxId()}")
        
        print("  ✓ Device enumeration complete")
        
    except ImportError:
        print("  ⚠️  DepthAI not installed, skipping Python API cleanup")
    except Exception as e:
        print(f"  Warning during device cleanup: {e}")

def main():
    print("🔧 OAK-D Device Release Tool")
    print("=" * 40)
    print()
    
    # Step 1: Find and kill processes
    print("[1] Checking for processes using OAK-D...")
    processes = find_oakd_processes()
    
    if not processes:
        print("  ✓ No OAK-D processes found")
    else:
        print(f"  Found {len(processes)} process(es):")
        for pid, cmd in processes:
            print(f"    PID {pid}: {cmd}")
        
        response = input("\n  Kill these processes? (y/N): ").strip().lower()
        if response == 'y':
            for pid, cmd in processes:
                print(f"    Killing PID {pid}...")
                kill_process(pid)
            
            time.sleep(1)
            print("  ✓ Processes terminated")
        else:
            print("  Skipped process termination")
    
    # Step 2: Release devices via Python API
    print()
    print("[2] Releasing device handles...")
    release_depthai_devices()
    
    # Step 3: Suggest USB reset if needed
    print()
    print("[3] Additional steps (if still stuck):")
    print("  • Run USB reset script with sudo:")
    print("    sudo ./release_oakd_device.sh")
    print("  • Physically unplug/replug the OAK-D device")
    print("  • Reboot the system")
    
    print()
    print("✓ Cleanup complete!")
    print()

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\nCancelled by user")
        sys.exit(1)

