#!/usr/bin/env python3
"""
Fixed vision runner that reuses device connection
"""
import depthai as dai
import cv2
import numpy as np
import os
import time

# Target classes
TARGET_LABELS = [
    "person", "cell phone", "bottle", "cup",
    "potted plant", "sports ball", "book",
    "wine glass", "vase"
]

# Full COCO label map
LABEL_MAP = [
    "person","bicycle","car","motorbike","aeroplane","bus","train","truck","boat",
    "traffic light","fire hydrant","stop sign","parking meter","bench","bird","cat",
    "dog","horse","sheep","cow","elephant","bear","zebra","giraffe","backpack",
    "umbrella","handbag","tie","suitcase","frisbee","skis","snowboard","sports ball",
    "kite","baseball bat","baseball glove","skateboard","surfboard","tennis racket",
    "bottle","wine glass","cup","fork","knife","spoon","bowl","banana","apple",
    "sandwich","orange","broccoli","carrot","hot dog","pizza","donut","cake","chair",
    "sofa","potted plant","bed","dining table","toilet","tvmonitor","laptop","mouse",
    "remote","keyboard","cell phone","microwave","oven","toaster","sink","refrigerator",
    "book","clock","vase","scissors","teddy bear","hair drier","toothbrush"
]

# Path to model
MODEL_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "models", "yolov8n_coco_640x352.blob"))

def create_pipeline():
    print("🔧 Building DepthAI pipeline (YOLOv8n @ 640x352)…")
    pipeline = dai.Pipeline()

    # RGB Camera
    cam_rgb = pipeline.create(dai.node.ColorCamera)
    cam_rgb.setPreviewSize(640, 352)
    cam_rgb.setPreviewKeepAspectRatio(False)
    cam_rgb.setInterleaved(False)
    cam_rgb.setFps(30)

    # Mono cameras
    monoL = pipeline.create(dai.node.MonoCamera)
    monoR = pipeline.create(dai.node.MonoCamera)
    monoL.setBoardSocket(dai.CameraBoardSocket.CAM_B)
    monoR.setBoardSocket(dai.CameraBoardSocket.CAM_C)
    monoL.setResolution(dai.MonoCameraProperties.SensorResolution.THE_480_P)
    monoR.setResolution(dai.MonoCameraProperties.SensorResolution.THE_480_P)

    # Stereo depth
    stereo = pipeline.create(dai.node.StereoDepth)
    stereo.setLeftRightCheck(True)
    stereo.setSubpixel(True)
    stereo.setDepthAlign(dai.CameraBoardSocket.CAM_A)
    stereo.initialConfig.setConfidenceThreshold(200)
    stereo.initialConfig.setMedianFilter(dai.MedianFilter.KERNEL_5x5)
    monoL.out.link(stereo.left)
    monoR.out.link(stereo.right)

    # Detection Network
    det = pipeline.create(dai.node.SpatialDetectionNetwork)
    det.setBlobPath(MODEL_PATH)
    det.setConfidenceThreshold(0.35)
    det.setBoundingBoxScaleFactor(0.5)
    det.setDepthLowerThreshold(100)
    det.setDepthUpperThreshold(4000)
    det.input.setBlocking(False)

    # Link RGB + Depth
    cam_rgb.preview.link(det.input)
    stereo.depth.link(det.inputDepth)

    # Outputs
    xout_rgb = pipeline.create(dai.node.SPIOut)
    xout_rgb.setStreamName("rgb")
    det.passthrough.link(xout_rgb.input)

    xout_det = pipeline.create(dai.node.SPIOut)
    xout_det.setStreamName("detections")
    det.out.link(xout_det.input)

    return pipeline

def draw_detections(frame, detections, z_ema):
    """Draw bounding boxes and labels on frame"""
    for det in detections:
        if det.label >= len(LABEL_MAP):
            continue
            
        label = LABEL_MAP[det.label]
        if label not in TARGET_LABELS:
            continue

        # Bounding box coordinates
        x1 = int(det.xmin * frame.shape[1])
        y1 = int(det.ymin * frame.shape[0])
        x2 = int(det.xmax * frame.shape[1])
        y2 = int(det.ymax * frame.shape[0])

        # Depth and confidence
        depth_m = det.spatialCoordinates.z / 1000.0
        conf = det.confidence * 100

        # Smooth depth readings
        prev = z_ema.get(label, depth_m)
        depth_m = 0.3 * depth_m + 0.7 * prev
        z_ema[label] = depth_m

        # Draw bounding box
        cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
        
        # Draw label with confidence and depth
        cv2.putText(
            frame,
            f"{label} {conf:.1f}% ({depth_m:.2f}m)",
            (x1, max(y1 - 10, 20)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            (0, 255, 0),
            2,
        )
        
        # Console output
        print(f"[Vision] {label} ({conf:.1f}%) – {depth_m:.2f} m away")

def main():
    print("🎥 Starting OAK-D Lite Vision System...")
    
    if not os.path.exists(MODEL_PATH):
        print(f"❌ Model not found at {MODEL_PATH}")
        return
    
    # Create pipeline
    pipeline = create_pipeline()
    z_ema = {}
    
    print("🚀 Starting vision system (connecting to device)...")
    start_time = time.monotonic()
    frame_count = 0

    try:
        with dai.Device() as device:
            print("✅ Device connected!")
            device.startPipeline(pipeline)
            print("✅ Pipeline started!")
            
            q_rgb = device.getOutputQueue("rgb", maxSize=4, blocking=False)
            q_det = device.getOutputQueue("detections", maxSize=4, blocking=False)

            while True:
                in_rgb = q_rgb.tryGet()
                in_det = q_det.tryGet()

                if in_rgb is not None:
                    frame = in_rgb.getCvFrame()
                    frame_count += 1

                    if in_det is not None:
                        detections = in_det.detections
                        draw_detections(frame, detections, z_ema)

                    cv2.imshow("Vision Detection", frame)

                if cv2.waitKey(1) == ord('q'):
                    break

    except Exception as e:
        print(f"❌ Error: {e}")
        return

    finally:
        end_time = time.monotonic()
        elapsed_time = end_time - start_time
        fps = frame_count / elapsed_time if elapsed_time > 0 else 0
        print(f"📊 Average FPS: {fps:.2f}")
        cv2.destroyAllWindows()
        print("🛑 Stopped. ✅ Vision module complete.")

if __name__ == "__main__":
    main()
