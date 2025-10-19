import depthai as dai
import cv2
import numpy as np

# ─────────────────────────────────────────────
# Target classes
# ─────────────────────────────────────────────
TARGET_LABELS = [
    "person", "cell phone", "bottle", "cup",
    "potted plant", "sports ball", "book",
    "wine glass", "vase"   # extra safety for bottle-like shapes
]

# ─────────────────────────────────────────────
# Full COCO label map
# ─────────────────────────────────────────────
LABEL_MAP = [
    "person","bicycle","car","motorbike","aeroplane","bus","train","truck","boat",
    "traffic light","fire hydrant","stop sign","parking meter","bench","bird","cat",
    "dog","horse","sheep","cow","elephant","bear","zebra","giraffe","backpack",
    "umbrella","handbag","tie","suitcase","frisbee","skis","snowboard","sports balls",
    "kite","baseball bat","baseball glove","skateboard","surfboard","tennis racket",
    "bottle","wine glass","cup","fork","knife","spoon","bowl","banana","apple",
    "sandwich","orange","broccoli","carrot","hot dog","pizza","donut","cake","chair",
    "sofa","potted plant","bed","dining table","toilet","tvmonitor","laptop","mouse",
    "remote","keyboard","cell phone","microwave","oven","toaster","sink","refrigerator",
    "book","clock","vase","scissors","teddy bear","hair drier","toothbrush"
]


# ─────────────────────────────────────────────
# Vision System (optimized for DepthAI v3.0.0)
# ─────────────────────────────────────────────
class VisionSystem:
    def __init__(self):
        print("🎥 Initializing OAK-D Lite Vision System (DepthAI v3.0.0)…")
        self.pipeline = self.create_pipeline()
        self.device = dai.Device(self.pipeline)
        self.q_rgb = self.device.getOutputQueue("rgb", maxSize=4, blocking=False)
        self.q_det = self.device.getOutputQueue("detections", maxSize=4, blocking=False)
        self._z_ema = {}

    def create_pipeline(self):
        print("🔧 Building DepthAI pipeline (YOLOv8n @ 640x352)…")
        pipeline = dai.Pipeline()

        # RGB Camera
        cam_rgb = pipeline.create(dai.node.ColorCamera)
        cam_rgb.setPreviewSize(640, 352)
        cam_rgb.setPreviewKeepAspectRatio(False)
        cam_rgb.setInterleaved(False)
        cam_rgb.setFps(30)

        # Mono cameras for stereo depth
        monoL = pipeline.create(dai.node.MonoCamera)
        monoR = pipeline.create(dai.node.MonoCamera)
        monoL.setBoardSocket(dai.CameraBoardSocket.LEFT)
        monoR.setBoardSocket(dai.CameraBoardSocket.RIGHT)
        monoL.setResolution(dai.MonoCameraProperties.SensorResolution.THE_480_P)
        monoR.setResolution(dai.MonoCameraProperties.SensorResolution.THE_480_P)

        # Stereo depth node
        stereo = pipeline.create(dai.node.StereoDepth)
        stereo.setLeftRightCheck(True)
        stereo.setSubpixel(True)
        stereo.setDepthAlign(dai.CameraBoardSocket.RGB)
        stereo.initialConfig.setConfidenceThreshold(200)
        stereo.initialConfig.setMedianFilter(dai.MedianFilter.KERNEL_5x5)
        monoL.out.link(stereo.left)
        monoR.out.link(stereo.right)

        # Spatial Detection Network (for YOLO with depth)
        detection_nn = pipeline.create(dai.node.SpatialDetectionNetwork)
        detection_nn.setBlobPath("models/yolov8n_coco_640x352.blob")
        detection_nn.setConfidenceThreshold(0.35)
        detection_nn.input.setBlocking(False)
        
        # Spatial detection specific settings
        detection_nn.setBoundingBoxScaleFactor(0.5)
        detection_nn.setDepthLowerThreshold(100)
        detection_nn.setDepthUpperThreshold(4000)

        # Link RGB camera and depth to detection network
        cam_rgb.preview.link(detection_nn.input)
        stereo.depth.link(detection_nn.inputDepth)

        # Output streams (using old API for v3.0.0)
        xout_rgb = pipeline.createXLinkOut()
        xout_rgb.setStreamName("rgb")
        detection_nn.passthrough.link(xout_rgb.input)

        xout_nn = pipeline.createXLinkOut()
        xout_nn.setStreamName("detections")
        detection_nn.out.link(xout_nn.input)

        return pipeline

    def run(self):
        print("✅ Starting detection. Press Q to quit.")
        cv2.namedWindow("Vision Detection", cv2.WINDOW_NORMAL)

        while True:
            in_rgb = self.q_rgb.tryGet()
            in_det = self.q_det.tryGet()

            if not in_rgb:
                continue

            frame = in_rgb.getCvFrame()

            # Apply contrast enhancement for better visibility
            if frame is not None:
                frame = cv2.convertScaleAbs(frame, alpha=1.2, beta=10)

            if frame is not None and in_det is not None:
                for det in in_det.detections:
                    # Get label (handle index out of range)
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

                    # Exponential moving average for smoother depth readings
                    key = label
                    prev = self._z_ema.get(key, depth_m)
                    depth_m = 0.3 * depth_m + 0.7 * prev
                    self._z_ema[key] = depth_m

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

            if frame is not None:
                cv2.imshow("Vision Detection", frame)
                
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break
                
        cv2.destroyAllWindows()
        print("🛑 Stopped. ✅ Vision module complete.")


if __name__ == "__main__":
    VisionSystem().run()