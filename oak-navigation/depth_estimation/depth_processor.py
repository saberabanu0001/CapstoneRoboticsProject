#!/usr/bin/env python3
"""
OAK-D Lite Depth Processing Module
Handles stereo depth map generation and processing for navigation
"""

import cv2
import depthai as dai
import numpy as np
from typing import Tuple, Optional, Dict
import time
from dataclasses import dataclass


@dataclass
class DepthConfig:
    """Configuration for depth processing"""
    # Stereo depth settings
    resolution: str = "400p"  # 400p, 720p, 800p
    extended_disparity: bool = False  # Closer minimum depth
    subpixel: bool = True  # Better accuracy for longer distances
    lr_check: bool = True  # Better occlusion handling
    median_filter: str = "KERNEL_7x7"  # Noise reduction
    
    # Depth range (in millimeters)
    min_depth: int = 300  # 30cm minimum
    max_depth: int = 10000  # 10m maximum
    
    # Processing settings
    fps: int = 15  # Reduced to 15fps to minimize firmware crashes (was 30fps)
                   # Lower FPS = less CPU load = more stable
    confidence_threshold: int = 200  # 0-255, higher = more confident
    
    # Grid settings for navigation
    grid_width: int = 64  # Divide depth map into grid
    grid_height: int = 48


class DepthProcessor:
    """
    Process depth data from OAK-D Lite for navigation
    
    KNOWN ISSUE: OAK-D "Silent Death" Bug
    ======================================
    The OAK-D camera may stop producing frames after ~20-30 frames due to:
    - USB3 connection instability (especially on Raspberry Pi)
    - Aggressive watchdog timeouts
    - Firmware CPU overload
    
    FIXES APPLIED:
    - Force USB2 mode (maxUsbSpeed=HIGH) - most important fix
    - Increase watchdog timeout to 4500ms
    - Reduce CPU load with setIsp3aFps(5)
    - Non-blocking queues
    - Health monitoring and detection
    
    To enable debug logging, set environment variable:
        export DEPTHAI_LEVEL=debug
        python3 your_script.py
    """
    
    def __init__(self, config: Optional[DepthConfig] = None):
        self.config = config or DepthConfig()
        self.pipeline = None
        self.device = None
        self.depth_queue = None
        self.rgb_queue = None
        
        # Statistics
        self.frame_count = 0
        self.fps = 0.0
        self.last_fps_time = time.time()
        
        # Health monitoring
        self.last_frame_time = time.time()
        self.none_frame_count = 0
        self.good_frame_count = 0
        
    def create_pipeline(self) -> dai.Pipeline:
        """Create DepthAI pipeline for stereo depth"""
        pipeline = dai.Pipeline()
        
        # Create nodes
        mono_left = pipeline.create(dai.node.MonoCamera)
        mono_right = pipeline.create(dai.node.MonoCamera)
        stereo = pipeline.create(dai.node.StereoDepth)
        
        # Output links - ONLY depth (removed RGB and disparity to reduce memory/CPU load)
        xout_depth = pipeline.create(dai.node.XLinkOut)
        xout_depth.setStreamName("depth")
        
        # Configure mono cameras
        resolution_map = {
            "400p": dai.MonoCameraProperties.SensorResolution.THE_400_P,
            "720p": dai.MonoCameraProperties.SensorResolution.THE_720_P,
            "800p": dai.MonoCameraProperties.SensorResolution.THE_800_P,
        }
        
        mono_resolution = resolution_map.get(self.config.resolution, 
                                            dai.MonoCameraProperties.SensorResolution.THE_400_P)
        
        mono_left.setResolution(mono_resolution)
        mono_left.setCamera("left")
        mono_left.setFps(self.config.fps)
        # Reduce CPU load by limiting 3A (auto-exposure/white-balance) updates
        mono_left.setIsp3aFps(5)  # Run 3A algorithms every 5 frames instead of every frame
        
        mono_right.setResolution(mono_resolution)
        mono_right.setCamera("right")
        mono_right.setFps(self.config.fps)
        mono_right.setIsp3aFps(5)
        
        # Configure stereo depth
        # Using HIGH_ACCURACY (less CPU) instead of HIGH_DENSITY to prevent crashes
        stereo.setDefaultProfilePreset(dai.node.StereoDepth.PresetMode.HIGH_ACCURACY)
        stereo.setLeftRightCheck(self.config.lr_check)
        stereo.setExtendedDisparity(self.config.extended_disparity)
        stereo.setSubpixel(self.config.subpixel)
        # Removed RGB alignment to reduce processing load
        
        # Median filter
        median_map = {
            "MEDIAN_OFF": dai.MedianFilter.MEDIAN_OFF,
            "KERNEL_3x3": dai.MedianFilter.KERNEL_3x3,
            "KERNEL_5x5": dai.MedianFilter.KERNEL_5x5,
            "KERNEL_7x7": dai.MedianFilter.KERNEL_7x7,
        }
        median = median_map.get(self.config.median_filter, dai.MedianFilter.KERNEL_7x7)
        stereo.initialConfig.setMedianFilter(median)
        
        # Set confidence threshold
        stereo.initialConfig.setConfidenceThreshold(self.config.confidence_threshold)
        
        # Linking - only depth output to minimize resource usage
        mono_left.out.link(stereo.left)
        mono_right.out.link(stereo.right)
        stereo.depth.link(xout_depth.input)
        
        return pipeline
    
    def start(self):
        """Start the depth processing pipeline"""
        print("[DepthProcessor] Starting OAK-D Lite...")
        
        # Enable debug logging to diagnose issues
        import os
        os.environ['DEPTHAI_LEVEL'] = 'warn'  # Set to 'debug' for detailed logs
        os.environ['DEPTHAI_WATCHDOG'] = '4500'  # Increase watchdog timeout to max (4.5s)
        
        self.pipeline = self.create_pipeline()
        
        # CRITICAL FIX: Force USB2 mode to avoid USB3 stability issues on Raspberry Pi
        # This is a known fix for the "silent death" frame freeze issue
        print("[DepthProcessor] Forcing USB2 mode (prevents freeze bug)...")
        
        # Retry logic for device connection (handles device-in-use errors)
        max_retries = 3
        retry_delay = 1.0
        
        for attempt in range(max_retries):
            try:
                self.device = dai.Device(self.pipeline, maxUsbSpeed=dai.UsbSpeed.HIGH)
                break  # Success!
            except RuntimeError as e:
                if "X_LINK_DEVICE_ALREADY_IN_USE" in str(e):
                    print(f"[DepthProcessor] Device busy (attempt {attempt + 1}/{max_retries})")
                    if attempt < max_retries - 1:
                        print(f"[DepthProcessor] Waiting {retry_delay}s before retry...")
                        time.sleep(retry_delay)
                        retry_delay *= 2  # Exponential backoff
                    else:
                        print("[DepthProcessor] ❌ Device still in use after retries")
                        print("[DepthProcessor] Try running: python oakd_navigation/release_oakd_device.py")
                        raise
                else:
                    # Different error, don't retry
                    raise
        
        # Set device logging level
        self.device.setLogLevel(dai.LogLevel.WARN)
        self.device.setLogOutputLevel(dai.LogLevel.WARN)
        
        # Get output queue (non-blocking to prevent pipeline stalls)
        # Only depth queue - RGB removed to reduce memory/CPU load and prevent crashes
        self.depth_queue = self.device.getOutputQueue(name="depth", maxSize=4, blocking=False)
        
        usb_speed = self.device.getUsbSpeed()
        print(f"[DepthProcessor] Started successfully")
        print(f"  USB Speed: {usb_speed}")
        print(f"  Resolution: {self.config.resolution}")
        print(f"  FPS: {self.config.fps}")
        print(f"  Depth range: {self.config.min_depth}-{self.config.max_depth}mm")
        print(f"  Watchdog: 4500ms (max)")
        
    def stop(self):
        """Stop the pipeline and close device"""
        if self.device:
            self.device.close()
            self.device = None
        print("[DepthProcessor] Stopped")
    
    def restart(self):
        """Restart the pipeline (recovery from silent death)"""
        print("[DepthProcessor] Restarting pipeline...")
        self.stop()
        time.sleep(1)  # Give hardware time to reset
        self.start()
        # Reset counters
        self.none_frame_count = 0
        self.good_frame_count = 0
        print("[DepthProcessor] Restart complete")
    
    def get_depth_frame(self) -> Optional[np.ndarray]:
        """Get latest depth frame in millimeters"""
        if not self.depth_queue:
            return None
        
        try:
            depth_data = self.depth_queue.tryGet()
            if depth_data is None:
                self.none_frame_count += 1
                
                # Detect "silent death" - no frames for extended period
                time_since_last = time.time() - self.last_frame_time
                if time_since_last > 5.0:  # 5 seconds without frames
                    print(f"[DepthProcessor] WARNING: Pipeline silent death detected!")
                    print(f"  No frames for {time_since_last:.1f}s (None:{self.none_frame_count}, Good:{self.good_frame_count})")
                    print(f"  This is a known OAK-D hardware issue. Consider restarting.")
                    # Reset counter to avoid spam
                    self.last_frame_time = time.time()
                
                return None
            
            # Got a good frame!
            self.good_frame_count += 1
            self.last_frame_time = time.time()
            
            # Update FPS
            self.frame_count += 1
            current_time = time.time()
            if current_time - self.last_fps_time > 1.0:
                self.fps = self.frame_count / (current_time - self.last_fps_time)
                self.frame_count = 0
                self.last_fps_time = current_time
            
            # Get depth frame (values in millimeters)
            depth_frame = depth_data.getFrame()
            return depth_frame
        
        except Exception as e:
            # Camera pipeline error - log it
            print(f"[DepthProcessor] ERROR getting frame: {e}")
            return None
    
    def get_rgb_frame(self) -> Optional[np.ndarray]:
        """
        Get latest RGB frame
        NOTE: RGB camera disabled to reduce resource usage and prevent firmware crashes
        """
        return None
    
    def process_depth_for_navigation(self, depth_frame: np.ndarray) -> Dict:
        """
        Process depth frame for navigation decisions
        Returns dictionary with navigation-relevant information
        """
        if depth_frame is None:
            return None
        
        # Clip depth to configured range
        depth_clipped = np.clip(depth_frame, self.config.min_depth, self.config.max_depth)
        
        # Create grid-based depth map
        grid_depth = self.create_depth_grid(depth_clipped)
        
        # Analyze depth zones
        zones = self.analyze_depth_zones(depth_clipped)
        
        # Find obstacles
        obstacles = self.detect_obstacles(depth_clipped)
        
        # Calculate safe directions
        safe_directions = self.calculate_safe_directions(grid_depth)
        
        return {
            'depth_frame': depth_frame,
            'depth_clipped': depth_clipped,
            'grid_depth': grid_depth,
            'zones': zones,
            'obstacles': obstacles,
            'safe_directions': safe_directions,
            'fps': self.fps,
            'timestamp': time.time()
        }
    
    def create_depth_grid(self, depth_frame: np.ndarray) -> np.ndarray:
        """
        Divide depth frame into grid and compute average depth per cell
        Returns grid with average depth values (in mm)
        """
        h, w = depth_frame.shape
        grid_h, grid_w = self.config.grid_height, self.config.grid_width
        
        cell_h = h // grid_h
        cell_w = w // grid_w
        
        grid = np.zeros((grid_h, grid_w), dtype=np.float32)
        
        for i in range(grid_h):
            for j in range(grid_w):
                y1, y2 = i * cell_h, (i + 1) * cell_h
                x1, x2 = j * cell_w, (j + 1) * cell_w
                
                cell = depth_frame[y1:y2, x1:x2]
                # Use median for robustness against outliers
                valid_depths = cell[cell > 0]
                if len(valid_depths) > 0:
                    grid[i, j] = np.median(valid_depths)
                else:
                    grid[i, j] = self.config.max_depth  # No data = far away
        
        return grid
    
    def analyze_depth_zones(self, depth_frame: np.ndarray) -> Dict:
        """
        Analyze depth in different zones (left, center, right, near, far)
        """
        h, w = depth_frame.shape
        
        # Divide into left, center, right
        left = depth_frame[:, :w//3]
        center = depth_frame[:, w//3:2*w//3]
        right = depth_frame[:, 2*w//3:]
        
        # Focus on lower half (ground level)
        lower_half_y = h // 2
        
        def get_zone_stats(zone):
            valid = zone[zone > 0]
            if len(valid) == 0:
                return {'min': self.config.max_depth, 'mean': self.config.max_depth, 
                       'median': self.config.max_depth}
            return {
                'min': float(np.min(valid)),
                'mean': float(np.mean(valid)),
                'median': float(np.median(valid))
            }
        
        return {
            'left': get_zone_stats(left[lower_half_y:, :]),
            'center': get_zone_stats(center[lower_half_y:, :]),
            'right': get_zone_stats(right[lower_half_y:, :]),
            'full': get_zone_stats(depth_frame[lower_half_y:, :])
        }
    
    def detect_obstacles(self, depth_frame: np.ndarray, 
                        obstacle_threshold: int = 1000) -> Dict:
        """
        Detect obstacles closer than threshold (default 1m)
        Returns obstacle map and statistics
        """
        # Create binary obstacle map
        obstacle_map = (depth_frame > 0) & (depth_frame < obstacle_threshold)
        
        # Count obstacles in different regions
        h, w = depth_frame.shape
        left_obstacles = np.sum(obstacle_map[:, :w//3])
        center_obstacles = np.sum(obstacle_map[:, w//3:2*w//3])
        right_obstacles = np.sum(obstacle_map[:, 2*w//3:])
        
        total_pixels = h * w
        obstacle_percentage = (np.sum(obstacle_map) / total_pixels) * 100
        
        return {
            'obstacle_map': obstacle_map,
            'left_count': int(left_obstacles),
            'center_count': int(center_obstacles),
            'right_count': int(right_obstacles),
            'total_percentage': float(obstacle_percentage),
            'has_obstacle': obstacle_percentage > 5.0  # 5% threshold
        }
    
    def calculate_safe_directions(self, grid_depth: np.ndarray, 
                                  safe_distance: int = 1500) -> Dict:
        """
        Calculate which directions are safe to move
        Returns dict with safety scores for different directions
        """
        grid_h, grid_w = grid_depth.shape
        
        # Focus on bottom third (ground level)
        ground_level = grid_depth[2*grid_h//3:, :]
        
        # Calculate average depth for each column (left to right)
        column_depths = np.mean(ground_level, axis=0)
        
        # Divide into 5 sectors: far-left, left, center, right, far-right
        sector_size = grid_w // 5
        sectors = []
        for i in range(5):
            start = i * sector_size
            end = (i + 1) * sector_size if i < 4 else grid_w
            sector_depth = np.mean(column_depths[start:end])
            is_safe = sector_depth > safe_distance
            sectors.append({
                'depth': float(sector_depth),
                'safe': bool(is_safe),
                'score': float(min(sector_depth / safe_distance, 2.0))  # 0-2 score
            })
        
        return {
            'far_left': sectors[0],
            'left': sectors[1],
            'center': sectors[2],
            'right': sectors[3],
            'far_right': sectors[4],
            'best_direction': self._get_best_direction(sectors)
        }
    
    def _get_best_direction(self, sectors: list) -> str:
        """Determine best direction from sector analysis"""
        direction_names = ['far_left', 'left', 'center', 'right', 'far_right']
        
        # Prefer center, then adjacent sectors
        preference_order = [2, 1, 3, 0, 4]  # center, left, right, far_left, far_right
        
        for idx in preference_order:
            if sectors[idx]['safe']:
                return direction_names[idx]
        
        # If nothing is safe, return direction with maximum depth
        max_idx = max(range(5), key=lambda i: sectors[i]['depth'])
        return direction_names[max_idx]
    
    def visualize_depth(self, depth_frame: np.ndarray) -> np.ndarray:
        """Create colorized visualization of depth frame"""
        if depth_frame is None:
            return None
        
        # Normalize to 0-255
        depth_normalized = np.interp(depth_frame, 
                                    (self.config.min_depth, self.config.max_depth), 
                                    (0, 255)).astype(np.uint8)
        
        # Apply colormap (closer = red/yellow, farther = blue/green)
        depth_colored = cv2.applyColorMap(depth_normalized, cv2.COLORMAP_TURBO)
        
        return depth_colored
    
    def __enter__(self):
        self.start()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()


if __name__ == "__main__":
    """Test depth processor"""
    print("Testing OAK-D Depth Processor...")
    print("Press 'q' to quit")
    
    config = DepthConfig(
        resolution="400p",
        fps=30,
        min_depth=300,
        max_depth=5000
    )
    
    with DepthProcessor(config) as processor:
        while True:
            # Get depth frame
            depth_frame = processor.get_depth_frame()
            rgb_frame = processor.get_rgb_frame()
            
            if depth_frame is not None:
                # Process for navigation
                nav_data = processor.process_depth_for_navigation(depth_frame)
                
                # Visualize
                depth_colored = processor.visualize_depth(depth_frame)
                
                # Add navigation info overlay
                if depth_colored is not None:
                    h, w = depth_colored.shape[:2]
                    
                    # Draw zones
                    zones = nav_data['zones']
                    y_pos = 30
                    cv2.putText(depth_colored, f"FPS: {processor.fps:.1f}", 
                               (10, y_pos), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
                    y_pos += 25
                    cv2.putText(depth_colored, f"L: {zones['left']['median']:.0f}mm", 
                               (10, y_pos), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
                    y_pos += 20
                    cv2.putText(depth_colored, f"C: {zones['center']['median']:.0f}mm", 
                               (10, y_pos), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
                    y_pos += 20
                    cv2.putText(depth_colored, f"R: {zones['right']['median']:.0f}mm", 
                               (10, y_pos), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
                    
                    # Show best direction
                    best_dir = nav_data['safe_directions']['best_direction']
                    y_pos += 30
                    cv2.putText(depth_colored, f"Best: {best_dir}", 
                               (10, y_pos), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
                    
                    # Show obstacle warning
                    if nav_data['obstacles']['has_obstacle']:
                        cv2.putText(depth_colored, "OBSTACLE!", 
                                   (w//2 - 60, 40), cv2.FONT_HERSHEY_SIMPLEX, 
                                   0.8, (0, 0, 255), 2)
                    
                    cv2.imshow("Depth Navigation View", depth_colored)
                
                if rgb_frame is not None:
                    cv2.imshow("RGB Camera", rgb_frame)
            
            if cv2.waitKey(1) == ord('q'):
                break
    
    cv2.destroyAllWindows()
    print("Test completed")

