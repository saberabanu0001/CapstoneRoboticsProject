#!/usr/bin/env python3
"""
Simple working vision system based on DepthAI examples
"""
import depthai as dai
import cv2
import time

def main():
    print("🎥 Starting Simple OAK-D Vision System...")
    
    # Create pipeline
    pipeline = dai.Pipeline()
    
    # RGB Camera
    cam_rgb = pipeline.create(dai.node.ColorCamera)
    cam_rgb.setPreviewSize(640, 352)
    cam_rgb.setInterleaved(False)
    cam_rgb.setFps(30)
    
    # Output
    xout_rgb = pipeline.create(dai.node.SPIOut)
    xout_rgb.setStreamName("rgb")
    cam_rgb.preview.link(xout_rgb.input)
    
    print("🚀 Starting camera preview...")
    
    try:
        with dai.Device() as device:
            print("✅ Device connected!")
            device.startPipeline(pipeline)
            print("✅ Pipeline started!")
            
            q_rgb = device.getOutputQueue(name="rgb", maxSize=4, blocking=False)
            
            while True:
                in_rgb = q_rgb.get()  # blocking call
                frame = in_rgb.getCvFrame()
                
                # Add some text to show it's working
                cv2.putText(frame, "OAK-D Lite Working!", (10, 30), 
                           cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
                
                cv2.imshow("OAK-D Lite Preview", frame)
                
                if cv2.waitKey(1) == ord('q'):
                    break
                    
    except Exception as e:
        print(f"❌ Error: {e}")
        return
    
    finally:
        cv2.destroyAllWindows()
        print("🛑 Stopped.")

if __name__ == "__main__":
    main()
