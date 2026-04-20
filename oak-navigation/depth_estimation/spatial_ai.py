#!/usr/bin/env python3
"""
Spatial AI Module for OAK-D Navigation
Integrates object detection with depth for spatial awareness
"""

import cv2
import depthai as dai
import numpy as np
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from pathlib import Path
import time


@dataclass
class SpatialObject:
    """Detected object with spatial coordinates"""
    label: str
    confidence: float
    bbox: Tuple[int, int, int, int]  # (x1, y1, x2, y2)
    spatial_coords: Tuple[float, float, float]  # (x, y, z) in mm
    distance: float  # Distance in meters
    angle: float  # Angle relative to robot heading (radians)
    
    def is_obstacle(self, obstacle_classes: List[str] = None) -> bool:
        """Check if object should be treated as obstacle"""
        if obstacle_classes is None:
            # Default obstacle classes
            obstacle_classes = [
                "person", "bicycle", "car", "motorbike", "bus", "truck",
                "chair", "sofa", "bed", "diningtable", "toilet",
                "bottle", "cup", "bowl", "backpack", "suitcase"
            ]
        return self.label.lower() in obstacle_classes


class SpatialAI:
    """
    Spatial AI detection using OAK-D with neural network
    Combines object detection with depth information
    """
    
    # COCO labels for MobileNet-SSD and YOLO
    COCO_LABELS = [
        "person", "bicycle", "car", "motorbike", "aeroplane", "bus", "train",
        "truck", "boat", "traffic light", "fire hydrant", "stop sign", "parking meter", "bench",
        "bird", "cat", "dog", "horse", "sheep", "cow", "elephant",
        "bear", "zebra", "giraffe", "backpack", "umbrella", "handbag", "tie",
        "suitcase", "frisbee", "skis", "snowboard", "sports ball", "kite", "baseball bat",
        "baseball glove", "skateboard", "surfboard", "tennis racket", "bottle", "wine glass", "cup",
        "fork", "knife", "spoon", "bowl", "banana", "apple", "sandwich",
        "orange", "broccoli", "carrot", "hot dog", "pizza", "donut", "cake",
        "chair", "sofa", "pottedplant", "bed", "diningtable", "toilet", "tvmonitor",
        "laptop", "mouse", "remote", "keyboard", "cell phone", "microwave", "oven",
        "toaster", "sink", "refrigerator", "book", "clock", "vase", "scissors",
        "teddy bear", "hair drier", "toothbrush"
    ]
    
    def __init__(self, 
                 model_path: Optional[str] = None,
                 confidence_threshold: float = 0.5,
                 iou_threshold: float = 0.5):
        """
        Initialize Spatial AI
        
        Args:
            model_path: Path to neural network blob file
            confidence_threshold: Minimum confidence for detections
            iou_threshold: IoU threshold for NMS
        """
        self.model_path = model_path
        self.confidence_threshold = confidence_threshold
        self.iou_threshold = iou_threshold
        
        self.pipeline = None
        self.device = None
        self.detection_queue = None
        self.rgb_queue = None
        self.depth_queue = None
        
        # Statistics
        self.fps = 0.0
        self.frame_count = 0
        self.last_fps_time = time.time()
        
        # Detection history for tracking
        self.detection_history = []
        self.max_history = 30
    
    def create_pipeline(self) -> dai.Pipeline:
        """Create DepthAI pipeline with spatial detection network"""
        pipeline = dai.Pipeline()
        
        # Create nodes
        cam_rgb = pipeline.create(dai.node.ColorCamera)
        mono_left = pipeline.create(dai.node.MonoCamera)
        mono_right = pipeline.create(dai.node.MonoCamera)
        stereo = pipeline.create(dai.node.StereoDepth)
        
        # Neural network node
        if self.model_path and Path(self.model_path).exists():
            # Use custom model
            detection_nn = pipeline.create(dai.node.YoloSpatialDetectionNetwork)
            detection_nn.setBlobPath(self.model_path)
        else:
            # Use MobileNet-SSD (built-in)
            detection_nn = pipeline.create(dai.node.MobileNetSpatialDetectionNetwork)
            # Note: You'll need to provide a blob file for this to work
            # For now, we'll create a basic setup
            print("[SpatialAI] Warning: No model specified, using default configuration")
        
        # Output nodes
        xout_rgb = pipeline.create(dai.node.XLinkOut)
        xout_nn = pipeline.create(dai.node.XLinkOut)
        xout_depth = pipeline.create(dai.node.XLinkOut)
        
        xout_rgb.setStreamName("rgb")
        xout_nn.setStreamName("detections")
        xout_depth.setStreamName("depth")
        
        # Configure RGB camera
        cam_rgb.setPreviewSize(416, 416)  # YOLO input size
        cam_rgb.setResolution(dai.ColorCameraProperties.SensorResolution.THE_1080_P)
        cam_rgb.setInterleaved(False)
        cam_rgb.setColorOrder(dai.ColorCameraProperties.ColorOrder.BGR)
        cam_rgb.setFps(30)
        
        # Configure mono cameras
        mono_left.setResolution(dai.MonoCameraProperties.SensorResolution.THE_400_P)
        mono_left.setCamera("left")
        mono_left.setFps(30)
        
        mono_right.setResolution(dai.MonoCameraProperties.SensorResolution.THE_400_P)
        mono_right.setCamera("right")
        mono_right.setFps(30)
        
        # Configure stereo depth
        stereo.setDefaultProfilePreset(dai.node.StereoDepth.PresetMode.HIGH_DENSITY)
        stereo.setLeftRightCheck(True)
        stereo.setSubpixel(True)
        stereo.setDepthAlign(dai.CameraBoardSocket.CAM_A)  # Align to RGB
        stereo.initialConfig.setMedianFilter(dai.MedianFilter.KERNEL_7x7)
        
        # Configure detection network
        detection_nn.setConfidenceThreshold(self.confidence_threshold)
        detection_nn.input.setBlocking(False)
        detection_nn.setBoundingBoxScaleFactor(0.5)
        detection_nn.setDepthLowerThreshold(100)  # 10cm minimum
        detection_nn.setDepthUpperThreshold(10000)  # 10m maximum
        
        # Linking
        mono_left.out.link(stereo.left)
        mono_right.out.link(stereo.right)
        
        cam_rgb.preview.link(detection_nn.input)
        detection_nn.passthrough.link(xout_rgb.input)
        detection_nn.out.link(xout_nn.input)
        
        stereo.depth.link(detection_nn.inputDepth)
        detection_nn.passthroughDepth.link(xout_depth.input)
        
        return pipeline
    
    def start(self):
        """Start the spatial AI pipeline"""
        print("[SpatialAI] Starting OAK-D with spatial detection...")
        
        try:
            self.pipeline = self.create_pipeline()
            self.device = dai.Device(self.pipeline)
            
            # Get output queues
            self.rgb_queue = self.device.getOutputQueue(name="rgb", maxSize=4, blocking=False)
            self.detection_queue = self.device.getOutputQueue(name="detections", maxSize=4, blocking=False)
            self.depth_queue = self.device.getOutputQueue(name="depth", maxSize=4, blocking=False)
            
            print("[SpatialAI] Started successfully")
        except Exception as e:
            print(f"[SpatialAI] Error starting: {e}")
            print("[SpatialAI] Note: You need a neural network blob file for full functionality")
            raise
    
    def stop(self):
        """Stop the pipeline"""
        if self.device:
            self.device.close()
            self.device = None
        print("[SpatialAI] Stopped")
    
    def get_detections(self) -> Tuple[Optional[np.ndarray], List[SpatialObject]]:
        """
        Get latest detections with spatial information
        
        Returns:
            Tuple of (rgb_frame, list of detected objects)
        """
        if not self.detection_queue or not self.rgb_queue:
            return None, []
        
        # Get latest frames
        rgb_data = self.rgb_queue.tryGet()
        detection_data = self.detection_queue.tryGet()
        
        if rgb_data is None or detection_data is None:
            return None, []
        
        # Update FPS
        self.frame_count += 1
        current_time = time.time()
        if current_time - self.last_fps_time > 1.0:
            self.fps = self.frame_count / (current_time - self.last_fps_time)
            self.frame_count = 0
            self.last_fps_time = current_time
        
        # Get RGB frame
        rgb_frame = rgb_data.getCvFrame()
        
        # Parse detections
        detections = detection_data.detections
        spatial_objects = []
        
        for detection in detections:
            if detection.confidence < self.confidence_threshold:
                continue
            
            # Get bounding box
            h, w = rgb_frame.shape[:2]
            x1 = int(detection.xmin * w)
            y1 = int(detection.ymin * h)
            x2 = int(detection.xmax * w)
            y2 = int(detection.ymax * h)
            
            # Get spatial coordinates
            spatial_coords = detection.spatialCoordinates
            x_mm = spatial_coords.x
            y_mm = spatial_coords.y
            z_mm = spatial_coords.z
            
            # Calculate distance and angle
            distance = math.sqrt(x_mm**2 + y_mm**2 + z_mm**2) / 1000.0  # Convert to meters
            angle = math.atan2(x_mm, z_mm)  # Angle from forward direction
            
            # Get label
            try:
                label = self.COCO_LABELS[detection.label]
            except (IndexError, AttributeError):
                label = f"class_{detection.label}"
            
            obj = SpatialObject(
                label=label,
                confidence=detection.confidence,
                bbox=(x1, y1, x2, y2),
                spatial_coords=(x_mm, y_mm, z_mm),
                distance=distance,
                angle=angle
            )
            
            spatial_objects.append(obj)
        
        # Update history
        self.detection_history.append(spatial_objects)
        if len(self.detection_history) > self.max_history:
            self.detection_history.pop(0)
        
        return rgb_frame, spatial_objects
    
    def get_navigation_context(self, detections: List[SpatialObject]) -> Dict:
        """
        Analyze detections for navigation context
        
        Returns:
            Dictionary with navigation-relevant information
        """
        if not detections:
            return {
                'has_obstacles': False,
                'closest_obstacle': None,
                'obstacles_by_zone': {'left': [], 'center': [], 'right': []},
                'people_detected': [],
                'vehicles_detected': []
            }
        
        # Categorize detections
        obstacles = [obj for obj in detections if obj.is_obstacle()]
        people = [obj for obj in detections if obj.label == "person"]
        vehicles = [obj for obj in detections if obj.label in ["car", "truck", "bus", "bicycle", "motorbike"]]
        
        # Find closest obstacle
        closest = min(obstacles, key=lambda o: o.distance) if obstacles else None
        
        # Divide into zones based on angle
        zones = {'left': [], 'center': [], 'right': []}
        
        for obj in obstacles:
            if obj.angle > math.radians(20):
                zones['left'].append(obj)
            elif obj.angle < math.radians(-20):
                zones['right'].append(obj)
            else:
                zones['center'].append(obj)
        
        return {
            'has_obstacles': len(obstacles) > 0,
            'closest_obstacle': closest,
            'obstacles_by_zone': zones,
            'people_detected': people,
            'vehicles_detected': vehicles,
            'total_detections': len(detections)
        }
    
    def visualize_detections(self, 
                            rgb_frame: np.ndarray, 
                            detections: List[SpatialObject]) -> np.ndarray:
        """Draw detections on RGB frame"""
        if rgb_frame is None:
            return None
        
        vis_frame = rgb_frame.copy()
        
        for obj in detections:
            x1, y1, x2, y2 = obj.bbox
            
            # Choose color based on distance
            if obj.distance < 1.0:
                color = (0, 0, 255)  # Red - very close
            elif obj.distance < 2.0:
                color = (0, 165, 255)  # Orange - close
            else:
                color = (0, 255, 0)  # Green - far
            
            # Draw bounding box
            cv2.rectangle(vis_frame, (x1, y1), (x2, y2), color, 2)
            
            # Draw label and info
            label_text = f"{obj.label} {obj.confidence*100:.0f}%"
            cv2.putText(vis_frame, label_text, (x1, y1 - 35), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
            
            distance_text = f"Dist: {obj.distance:.2f}m"
            cv2.putText(vis_frame, distance_text, (x1, y1 - 20), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1)
            
            angle_text = f"Angle: {math.degrees(obj.angle):.0f}°"
            cv2.putText(vis_frame, angle_text, (x1, y1 - 5), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1)
        
        # Draw FPS
        cv2.putText(vis_frame, f"FPS: {self.fps:.1f}", (10, 30), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        
        # Draw detection count
        cv2.putText(vis_frame, f"Detections: {len(detections)}", (10, 60), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        
        return vis_frame
    
    def __enter__(self):
        self.start()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()


# Import math for angle calculations
import math


if __name__ == "__main__":
    """Test spatial AI (requires neural network blob)"""
    print("Testing Spatial AI Module")
    print("Note: This requires a neural network blob file to work properly")
    print("Press 'q' to quit")
    
    try:
        # You'll need to provide a model path
        # Example: model_path = "/path/to/yolo-v4-tiny.blob"
        spatial_ai = SpatialAI(
            model_path=None,  # Will use default if available
            confidence_threshold=0.5
        )
        
        with spatial_ai:
            while True:
                # Get detections
                rgb_frame, detections = spatial_ai.get_detections()
                
                if rgb_frame is not None:
                    # Get navigation context
                    nav_context = spatial_ai.get_navigation_context(detections)
                    
                    # Visualize
                    vis_frame = spatial_ai.visualize_detections(rgb_frame, detections)
                    
                    if vis_frame is not None:
                        # Add navigation info
                        y_pos = 100
                        if nav_context['has_obstacles']:
                            closest = nav_context['closest_obstacle']
                            if closest:
                                cv2.putText(vis_frame, 
                                          f"Closest: {closest.label} at {closest.distance:.2f}m", 
                                          (10, y_pos), cv2.FONT_HERSHEY_SIMPLEX, 
                                          0.6, (0, 0, 255), 2)
                        
                        cv2.imshow("Spatial AI Detection", vis_frame)
                
                if cv2.waitKey(1) == ord('q'):
                    break
        
        cv2.destroyAllWindows()
        print("Test completed")
        
    except Exception as e:
        print(f"Error: {e}")
        print("\nTo use Spatial AI, you need:")
        print("1. A trained neural network blob file (YOLO or MobileNet)")
        print("2. The blob file should be compatible with OAK-D")
        print("\nYou can download pre-trained models from:")
        print("https://github.com/luxonis/depthai-model-zoo")

