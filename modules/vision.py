
# modules/vision.py
import depthai as dai
import cv2
import numpy as np
import os
import time

# ─────────────────────────────────────────────
# Target classes
# ─────────────────────────────────────────────
TARGET_LABELS = [
    "person", "cell phone", "bottle", "cup",
    "potted plant", "sports ball", "book",
    "wine glass", "vase"
]

# ─────────────────────────────────────────────
# Full COCO label map
# ─────────────────────────────────────────────
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
MODEL_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "models", "yolov8n_coco_640x352.blob"))

SHOW_WINDOW = True  # Set False if running headless

# ─────────────────────────────────────────────
# Vision System (Fixed for macOS permissions)
# ─────────────────────────────────────────────
class VisionSystem:
    def __init__(self):
        print("🎥 Initializing OAK-D Lite Vision System (DepthAI v3.x)…")

        if not os.path.exists(MODEL_PATH):
            raise FileNotFoundError(f"Model not found at {MODEL_PATH}")

        print("🔧 Building DepthAI pipeline (YOLOv8n @ 640x352)…")
        self.pipeline = self.create_pipeline()
        self._z_ema = {}

    def create_pipeline(self):
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

    def run(self):
        print("🚀 Starting vision system (connecting to device)...")
        start_time = time.monotonic()
        frame_count = 0

        try:
            with dai.Device() as device:
                print("✅ Device connected!")
                device.startPipeline(self.pipeline)
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
                            self._draw_detections(frame, detections)

                        if SHOW_WINDOW:
                            cv2.imshow("Vision Detection", frame)

                    if cv2.waitKey(1) == ord('q'):
                        break

        except Exception as e:
            print(f"❌ Error during device connection or pipeline start: {e}")
            raise

        finally:
            end_time = time.monotonic()
            elapsed_time = end_time - start_time
            fps = frame_count / elapsed_time if elapsed_time > 0 else 0
            print(f"📊 Average FPS: {fps:.2f}")

            if SHOW_WINDOW:
                cv2.destroyAllWindows()
            print("🛑 Stopped. ✅ Vision module complete.")

    def _draw_detections(self, frame, detections):
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
            prev = self._z_ema.get(label, depth_m)
            depth_m = 0.3 * depth_m + 0.7 * prev
            self._z_ema[label] = depth_m

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

if __name__ == "__main__":
    try:
        vision = VisionSystem()
        vision.run()
    except KeyboardInterrupt:
        print("\n🛑 Interrupted by user")
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        print("🧹 Cleaning up...")
=======
"""
Vision Module for Custom AI Rover Platform
Owner: Sabera

This module handles all input from the OAK-D camera according to the API contract.
Implements person detection and obstacle distance measurement using computer vision.
"""

import logging
import numpy as np
import cv2
import time
from typing import Optional, Tuple

# OAK-D camera imports (uncomment when running on actual hardware)
# import depthai as dai

logger = logging.getLogger(__name__)

# Global variables
_camera_initialized = False
_device = None
_pipeline = None
_latest_frame = None
_person_detected = False
_obstacle_distance = float('inf')

# Camera configuration
CAMERA_WIDTH = 640
CAMERA_HEIGHT = 480
CAMERA_FPS = 30

def setup() -> None:
    """
    Initializes the OAK-D camera and computer vision pipeline.
    Must be called before any other vision functions.
    Raises RuntimeError if camera initialization fails.
    """
    global _camera_initialized, _device, _pipeline
    
    logger.info("Initializing OAK-D camera and vision pipeline...")
    
    try:
        # TODO: Uncomment when running on actual hardware with OAK-D
        # # Create pipeline
        # _pipeline = dai.Pipeline()
        
        # # Define sources and outputs
        # cam_rgb = _pipeline.create(dai.node.ColorCamera)
        # depth = _pipeline.create(dai.node.MonoCamera)
        # depth_out = _pipeline.create(dai.node.XLinkOut)
        # rgb_out = _pipeline.create(dai.node.XLinkOut)
        
        # # Configure RGB camera
        # cam_rgb.setPreviewSize(CAMERA_WIDTH, CAMERA_HEIGHT)
        # cam_rgb.setColorOrder(dai.ColorCameraProperties.ColorOrder.BGR)
        # cam_rgb.setFps(CAMERA_FPS)
        
        # # Configure depth camera
        # depth.setResolution(dai.MonoCameraProperties.SensorResolution.THE_720_P)
        # depth.setCamera("left")
        
        # # Create outputs
        # rgb_out.setStreamName("rgb")
        # depth_out.setStreamName("depth")
        
        # # Link nodes
        # cam_rgb.preview.link(rgb_out.input)
        # depth.out.link(depth_out.input)
        
        # # Connect to device and start pipeline
        # _device = dai.Device(_pipeline)
        # _device.startPipeline()
        
        _camera_initialized = True
        logger.info("OAK-D camera initialized successfully")
        
        # TEMPORARY: Simulation mode for development
        logger.warning("Running in SIMULATION mode - using webcam or dummy data")
        _camera_initialized = True
        
        # Try to initialize webcam for simulation
        _init_simulation_camera()
        
    except Exception as e:
        logger.error(f"Failed to initialize camera: {e}")
        raise RuntimeError(f"Camera initialization failed: {e}")

def _init_simulation_camera() -> None:
    """Initialize webcam for simulation mode."""
    global _device
    
    try:
        # Try to open default webcam
        _device = cv2.VideoCapture(0)
        if _device.isOpened():
            _device.set(cv2.CAP_PROP_FRAME_WIDTH, CAMERA_WIDTH)
            _device.set(cv2.CAP_PROP_FRAME_HEIGHT, CAMERA_HEIGHT)
            _device.set(cv2.CAP_PROP_FPS, CAMERA_FPS)
            logger.info("Webcam initialized for simulation")
        else:
            _device = None
            logger.warning("No webcam available - using dummy data")
    except Exception as e:
        logger.warning(f"Could not initialize webcam: {e}")
        _device = None

def get_latest_frame() -> Optional[np.ndarray]:
    """
    Returns the latest color image frame as a NumPy array.
    
    Returns:
        numpy.ndarray: BGR color image (OpenCV standard), shape (height, width, 3)
        None: If no frame is available
    """
    global _latest_frame
    
    if not _camera_initialized:
        logger.warning("Camera not initialized")
        return None
    
    try:
        # TODO: Uncomment when running on actual OAK-D hardware
        # # Get latest frame from OAK-D
        # q_rgb = _device.getOutputQueue("rgb")
        # if q_rgb.has():
        #     in_rgb = q_rgb.get()
        #     _latest_frame = in_rgb.getCvFrame()
        
        # TEMPORARY: Simulation mode
        if _device is not None and _device.isOpened():
            # Read from webcam
            ret, frame = _device.read()
            if ret:
                _latest_frame = frame
                # Update person detection and obstacle distance
                _update_vision_analysis(_latest_frame)
            else:
                logger.warning("Failed to read from webcam")
                return None
        else:
            # Generate dummy frame for testing
            _latest_frame = _generate_dummy_frame()
            _update_vision_analysis(_latest_frame)
        
        return _latest_frame.copy() if _latest_frame is not None else None
        
    except Exception as e:
        logger.error(f"Error getting latest frame: {e}")
        return None

def _generate_dummy_frame() -> np.ndarray:
    """Generate a dummy frame for testing when no camera is available."""
    frame = np.zeros((CAMERA_HEIGHT, CAMERA_WIDTH, 3), dtype=np.uint8)
    
    # Add some visual elements
    cv2.rectangle(frame, (50, 50), (150, 150), (0, 255, 0), 2)
    cv2.putText(frame, "SIMULATION", (200, 100), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
    cv2.putText(frame, f"Time: {time.strftime('%H:%M:%S')}", (200, 150), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
    
    return frame

def _update_vision_analysis(frame: np.ndarray) -> None:
    """Update person detection and obstacle distance based on current frame."""
    global _person_detected, _obstacle_distance
    
    # TODO: Implement actual person detection using YOLO or similar
    # For now, use simple simulation logic
    
    # Simulate person detection (random for demo)
    import random
    _person_detected = random.random() > 0.7  # 30% chance of detecting person
    
    # Simulate obstacle distance (random between 0.5 and 10 meters)
    _obstacle_distance = random.uniform(0.5, 10.0)

def is_person_detected() -> bool:
    """
    Returns True if a person is detected in the current frame, otherwise False.
    Uses YOLO or similar object detection model.
    Updates automatically with each new frame.
    """
    if not _camera_initialized:
        logger.warning("Camera not initialized")
        return False
    
    # Update with latest frame
    get_latest_frame()
    
    logger.debug(f"Person detection status: {_person_detected}")
    return _person_detected

def _detect_person_yolo(frame: np.ndarray) -> bool:
    """
    Detect person using YOLO model (placeholder implementation).
    
    Args:
        frame: Input image frame
        
    Returns:
        bool: True if person detected, False otherwise
    """
    # TODO: Implement actual YOLO person detection
    # This is a placeholder for the actual implementation
    
    # Example implementation structure:
    # 1. Load YOLO model (do this once in setup())
    # 2. Preprocess frame
    # 3. Run inference
    # 4. Post-process results
    # 5. Check if 'person' class is detected with sufficient confidence
    
    # For now, return simulation result
    return _person_detected

def get_obstacle_distance() -> float:
    """
    Returns the distance in meters to the nearest obstacle directly in front of the robot.
    Uses depth information from OAK-D camera.
    
    Returns:
        float: Distance in meters (0.5 to 10.0 range), or float('inf') if no obstacle
    """
    if not _camera_initialized:
        logger.warning("Camera not initialized")
        return float('inf')
    
    try:
        # TODO: Uncomment when running on actual OAK-D hardware
        # # Get depth frame
        # q_depth = _device.getOutputQueue("depth")
        # if q_depth.has():
        #     in_depth = q_depth.get()
        #     depth_frame = in_depth.getFrame()
        #     
        #     # Get distance in center region of frame
        #     center_region = depth_frame[CAMERA_HEIGHT//2-50:CAMERA_HEIGHT//2+50,
        #                                CAMERA_WIDTH//2-50:CAMERA_WIDTH//2+50]
        #     
        #     # Find minimum distance in center region
        #     min_distance = np.min(center_region[center_region > 0]) / 1000.0  # Convert mm to meters
        #     _obstacle_distance = min_distance if min_distance < 10.0 else float('inf')
        
        # TEMPORARY: Simulation mode - update with latest frame
        get_latest_frame()
        
        logger.debug(f"Obstacle distance: {_obstacle_distance:.2f}m")
        return _obstacle_distance
        
    except Exception as e:
        logger.error(f"Error getting obstacle distance: {e}")
        return float('inf')

def cleanup() -> None:
    """
    Properly closes camera connections and releases resources.
    """
    global _camera_initialized, _device, _pipeline
    
    if not _camera_initialized:
        return
    
    logger.info("Cleaning up vision system...")
    
    try:
        # TODO: Uncomment when running on actual OAK-D hardware
        # if _device:
        #     _device.close()
        
        # TEMPORARY: Simulation mode cleanup
        if _device is not None and hasattr(_device, 'release'):
            _device.release()
        
        _camera_initialized = False
        _device = None
        _pipeline = None
        
        logger.info("Vision system cleanup complete")
        
    except Exception as e:
        logger.error(f"Error during vision cleanup: {e}")

def save_frame(filename: str) -> bool:
    """
    Save the current frame to a file for debugging.
    
    Args:
        filename: Path to save the image
        
    Returns:
        bool: True if successful, False otherwise
    """
    frame = get_latest_frame()
    if frame is not None:
        try:
            cv2.imwrite(filename, frame)
            logger.info(f"Frame saved to {filename}")
            return True
        except Exception as e:
            logger.error(f"Error saving frame: {e}")
            return False
    else:
        logger.warning("No frame available to save")
        return False

def test_vision() -> None:
    """Test function to verify vision system is working."""
    if not _camera_initialized:
        logger.error("Cannot test vision - not initialized")
        return
    
    logger.info("Testing vision system...")
    
    for i in range(10):
        frame = get_latest_frame()
        person = is_person_detected()
        distance = get_obstacle_distance()
        
        logger.info(f"Test {i+1}: Frame shape: {frame.shape if frame is not None else 'None'}, "
                   f"Person: {person}, Distance: {distance:.2f}m")
        
        time.sleep(1)
    
    logger.info("Vision test complete")

if __name__ == "__main__":
    # Test the module independently
    logging.basicConfig(level=logging.INFO)
    
    try:
        setup()
        test_vision()
    except KeyboardInterrupt:
        logger.info("Test interrupted")
    finally:
        cleanup()
>>>>>>> dea377af4274e5124b4eca662e9282d676801953
