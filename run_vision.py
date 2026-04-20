#!/usr/bin/env python3
"""
Simple script to run vision module with proper permissions
"""
import depthai as dai
import sys
import os

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def main():
    print("🔧 Fixing DepthAI permissions...")
    
    # First, try to fix permissions by creating a device
    try:
        device = dai.Device()
        print(f"✅ Device connected: {device.getDeviceName()}")
        device.close()
        print("✅ Permissions fixed!")
    except Exception as e:
        print(f"❌ Permission fix failed: {e}")
        return
    
    # Now import and run the vision module
    try:
        from modules.vision import VisionSystem
        print("🚀 Starting vision system...")
        vision = VisionSystem()
        vision.run()
    except Exception as e:
        print(f"❌ Vision system failed: {e}")

if __name__ == "__main__":
    main()
