#!/usr/bin/env python3
"""
Navigation Controller - Main integration module
Combines depth processing, obstacle avoidance, and path planning
"""

import time
import threading
import math
from typing import Optional, Callable, Tuple, Dict
from enum import Enum
from dataclasses import dataclass

from depth_processor import DepthProcessor, DepthConfig
from obstacle_avoidance import ObstacleAvoidance, AvoidanceStrategy, NavigationCommand
from path_planner import PathPlanner, PlannerType, Waypoint, Path, OccupancyGrid


class NavigationMode(Enum):
    """Navigation operating modes"""
    MANUAL = "manual"  # Manual control only
    ASSISTED = "assisted"  # Manual with obstacle avoidance
    AUTONOMOUS = "autonomous"  # Full autonomous navigation
    WAYPOINT = "waypoint"  # Follow waypoint list
    EXPLORE = "explore"  # Autonomous exploration


@dataclass
class NavigationState:
    """Current navigation state"""
    mode: NavigationMode
    is_moving: bool
    current_position: Optional[Waypoint]
    current_heading: float  # radians
    target_waypoint: Optional[Waypoint]
    current_path: Optional[Path]
    obstacles_detected: bool
    emergency_stop: bool
    last_command: Optional[NavigationCommand]
    uptime: float


class NavigationController:
    """
    Main navigation controller integrating all components
    """
    
    def __init__(self,
                 depth_config: Optional[DepthConfig] = None,
                 avoidance_strategy: AvoidanceStrategy = AvoidanceStrategy.POTENTIAL_FIELD,
                 planner_type: PlannerType = PlannerType.ASTAR,
                 update_rate: float = 10.0):  # Hz
        """
        Initialize navigation controller
        
        Args:
            depth_config: Configuration for depth processor
            avoidance_strategy: Obstacle avoidance algorithm
            planner_type: Path planning algorithm
            update_rate: Control loop frequency in Hz
        """
        # Components
        self.depth_processor = DepthProcessor(depth_config or DepthConfig())
        self.obstacle_avoider = ObstacleAvoidance(
            strategy=avoidance_strategy,
            safe_distance=1.5,
            max_speed=0.5
        )
        
        # Occupancy grid and path planner
        self.occupancy_grid = OccupancyGrid(width=20.0, height=20.0, resolution=0.1)
        self.path_planner = PathPlanner(planner_type, self.occupancy_grid)
        
        # State
        self.mode = NavigationMode.MANUAL
        self.is_running = False
        self.is_moving = False
        self.emergency_stop = False
        self.emergency_stop_time = None  # Track when emergency stop started
        self.stuck_recovery_active = False
        self.recovery_start_time = None
        self.recovery_turn_direction = None  # Which way we turned during recovery
        self.post_recovery_bias = None  # Direction bias after recovery
        self.post_recovery_time = None  # When we completed recovery
        
        # Position tracking (requires external odometry/SLAM)
        self.current_position = Waypoint(10.0, 10.0)  # Center of grid
        self.current_heading = 0.0  # radians
        
        # Navigation targets
        self.target_waypoint = None
        self.waypoint_queue = []
        self.current_path = None
        
        # Control loop
        self.update_rate = update_rate
        self.control_thread = None
        self.start_time = time.time()
        
        # Callbacks for motor control
        self.velocity_callback: Optional[Callable[[float, float], None]] = None
        self.stop_callback: Optional[Callable[[], None]] = None
        
        # Statistics
        self.total_distance_traveled = 0.0
        self.last_nav_data = None
    
    def set_velocity_callback(self, callback: Callable[[float, float], None]):
        """
        Set callback for sending velocity commands to robot
        
        Args:
            callback: Function(linear_vel, angular_vel) to control robot
        """
        self.velocity_callback = callback
    
    def set_stop_callback(self, callback: Callable[[], None]):
        """
        Set callback for emergency stop
        
        Args:
            callback: Function() to stop robot immediately
        """
        self.stop_callback = callback
    
    def start(self):
        """Start the navigation controller"""
        if self.is_running:
            print("[NavController] Already running")
            return
        
        print("[NavController] Starting navigation controller...")
        
        # Start depth processor
        self.depth_processor.start()
        
        # Start control loop
        self.is_running = True
        self.control_thread = threading.Thread(target=self._control_loop, daemon=True)
        self.control_thread.start()
        
        self.start_time = time.time()
        print(f"[NavController] Started in {self.mode.value} mode")
    
    def stop(self):
        """Stop the navigation controller"""
        if not self.is_running:
            return
        
        print("[NavController] Stopping navigation controller...")
        
        # Stop control loop
        self.is_running = False
        if self.control_thread:
            self.control_thread.join(timeout=2.0)
        
        # Stop robot
        self._send_stop_command()
        
        # Stop depth processor
        self.depth_processor.stop()
        
        print("[NavController] Stopped")
    
    def set_mode(self, mode: NavigationMode):
        """Change navigation mode"""
        print(f"[NavController] Changing mode: {self.mode.value} -> {mode.value}")
        self.mode = mode
        
        if mode == NavigationMode.MANUAL:
            # Clear autonomous navigation state
            self.target_waypoint = None
            self.current_path = None
            self.waypoint_queue.clear()
    
    def set_target(self, waypoint: Waypoint):
        """
        Set navigation target
        
        Args:
            waypoint: Target waypoint to navigate to
        """
        print(f"[NavController] Setting target: ({waypoint.x:.2f}, {waypoint.y:.2f})")
        self.target_waypoint = waypoint
        
        # Plan path if in autonomous mode
        if self.mode in [NavigationMode.AUTONOMOUS, NavigationMode.WAYPOINT]:
            self._plan_path_to_target()
    
    def add_waypoint(self, waypoint: Waypoint):
        """Add waypoint to queue"""
        self.waypoint_queue.append(waypoint)
        print(f"[NavController] Added waypoint: ({waypoint.x:.2f}, {waypoint.y:.2f})")
        
        if self.target_waypoint is None and self.waypoint_queue:
            self.set_target(self.waypoint_queue.pop(0))
    
    def clear_waypoints(self):
        """Clear all waypoints"""
        self.waypoint_queue.clear()
        self.target_waypoint = None
        self.current_path = None
        print("[NavController] Cleared all waypoints")
    
    def emergency_stop_trigger(self):
        """Trigger emergency stop"""
        print("[NavController] EMERGENCY STOP TRIGGERED")
        self.emergency_stop = True
        self._send_stop_command()
    
    def reset_emergency_stop(self):
        """Reset emergency stop"""
        print("[NavController] Emergency stop reset")
        self.emergency_stop = False
    
    def update_position(self, x: float, y: float, heading: float):
        """
        Update robot position (from external odometry/SLAM)
        
        Args:
            x, y: Position in meters
            heading: Heading in radians
        """
        old_pos = self.current_position
        self.current_position = Waypoint(x, y)
        self.current_heading = heading
        
        # Update distance traveled
        if old_pos:
            self.total_distance_traveled += old_pos.distance_to(self.current_position)
        
        # Update occupancy grid robot position
        self.occupancy_grid.robot_x = x
        self.occupancy_grid.robot_y = y
        self.occupancy_grid.robot_heading = heading
    
    def get_state(self) -> NavigationState:
        """Get current navigation state"""
        return NavigationState(
            mode=self.mode,
            is_moving=self.is_moving,
            current_position=self.current_position,
            current_heading=self.current_heading,
            target_waypoint=self.target_waypoint,
            current_path=self.current_path,
            obstacles_detected=self.last_nav_data is not None and 
                             self.last_nav_data.get('obstacles', {}).get('has_obstacle', False),
            emergency_stop=self.emergency_stop,
            last_command=self.obstacle_avoider.last_command,
            uptime=time.time() - self.start_time
        )
    
    def _control_loop(self):
        """Main control loop running at update_rate Hz"""
        loop_period = 1.0 / self.update_rate
        
        while self.is_running:
            loop_start = time.time()
            
            try:
                # Get depth data
                depth_frame = self.depth_processor.get_depth_frame()
                
                # Debug: Track frame reception
                if not hasattr(self, '_frame_count'):
                    self._frame_count = 0
                    self._none_count = 0
                
                if depth_frame is not None:
                    self._frame_count += 1
                else:
                    self._none_count += 1
                    if self._none_count % 50 == 0:  # Log every 50 None frames
                        print(f"[NavController] WARNING: No depth frames! None:{self._none_count}, Good:{self._frame_count}")
                
                if depth_frame is not None:
                    # Process depth for navigation
                    nav_data = self.depth_processor.process_depth_for_navigation(depth_frame)
                    self.last_nav_data = nav_data
                    
                    # Update occupancy grid (skip for now - can be slow)
                    # robot_pos = (
                    #     self.current_position.x,
                    #     self.current_position.y,
                    #     self.current_heading
                    # )
                    # self.occupancy_grid.update_from_depth(nav_data, robot_pos)
                    
                    # Execute navigation based on mode
                    if self.mode == NavigationMode.MANUAL:
                        # Manual mode - no autonomous control
                        pass
                    
                    elif self.mode == NavigationMode.ASSISTED:
                        # Assisted mode - obstacle avoidance only
                        # (User provides base commands, we modify for safety)
                        pass
                    
                    elif self.mode == NavigationMode.AUTONOMOUS:
                        self._autonomous_navigation(nav_data)
                    
                    elif self.mode == NavigationMode.WAYPOINT:
                        self._waypoint_navigation(nav_data)
                    
                    elif self.mode == NavigationMode.EXPLORE:
                        self._exploration_navigation(nav_data)
                
            except Exception as e:
                print(f"[NavController] Control loop error: {e}")
                import traceback
                traceback.print_exc()
                # Don't stop - keep trying
                time.sleep(0.1)
            
            # Maintain loop rate
            elapsed = time.time() - loop_start
            sleep_time = max(0, loop_period - elapsed)
            time.sleep(sleep_time)
    
    def _autonomous_navigation(self, nav_data: Dict):
        """Autonomous navigation to target with stuck recovery"""
        if self.target_waypoint is None:
            self._send_stop_command()
            return
        
        # Check if reached target
        distance_to_target = self.current_position.distance_to(self.target_waypoint)
        if distance_to_target < 0.3:  # 30cm threshold
            print(f"[NavController] Reached target!")
            self.target_waypoint = None
            self.current_path = None
            self._send_stop_command()
            
            # Check for next waypoint in queue
            if self.waypoint_queue:
                self.set_target(self.waypoint_queue.pop(0))
            return
        
        # Calculate goal direction
        dx = self.target_waypoint.x - self.current_position.x
        dy = self.target_waypoint.y - self.current_position.y
        goal_direction = math.atan2(dy, dx)
        
        # Get navigation command from obstacle avoider
        command = self.obstacle_avoider.compute_command(nav_data, goal_direction)
        
        # STUCK DETECTION AND RECOVERY (same as exploration)
        if command.stop:
            if self.emergency_stop_time is None:
                self.emergency_stop_time = time.time()
                print("[NavController] Emergency stop activated")
            else:
                stuck_duration = time.time() - self.emergency_stop_time
                if stuck_duration > 1.5:
                    self._execute_stuck_recovery(nav_data, stuck_duration)
                    return
        else:
            if self.emergency_stop_time is not None:
                print("[NavController] Emergency cleared, resuming navigation")
            self.emergency_stop_time = None
            self.stuck_recovery_active = False
        
        # Send command to robot
        self._send_velocity_command(command)
    
    def _waypoint_navigation(self, nav_data: Dict):
        """Navigate through waypoint list"""
        # Similar to autonomous but with path following
        if self.current_path and self.current_path.is_valid:
            # Follow path
            next_wp = self.current_path.get_next_waypoint(
                self.current_position,
                lookahead_distance=0.5
            )
            
            if next_wp:
                # Temporarily set as target for this iteration
                temp_target = self.target_waypoint
                self.target_waypoint = next_wp
                self._autonomous_navigation(nav_data)
                self.target_waypoint = temp_target
            else:
                # Path completed
                self._autonomous_navigation(nav_data)
        else:
            # No path - use direct navigation
            self._autonomous_navigation(nav_data)
    
    def _exploration_navigation(self, nav_data: Dict):
        """Autonomous exploration behavior with stuck recovery"""
        # Debug counter
        if not hasattr(self, '_explore_count'):
            self._explore_count = 0
        self._explore_count += 1
        if self._explore_count % 50 == 0:  # Every 5 seconds at 10Hz
            print(f"[NavController] Exploration calls: {self._explore_count}")
        
        # Get command from obstacle avoider
        safe_dirs = nav_data['safe_directions']
        best_dir = safe_dirs['best_direction']
        
        # Apply post-recovery bias to avoid going back to the same obstacle
        if self.post_recovery_bias is not None and self.post_recovery_time is not None:
            time_since_recovery = time.time() - self.post_recovery_time
            
            # Apply bias for 5 seconds after recovery
            if time_since_recovery < 5.0:
                # Prefer continuing in the direction we turned during recovery
                # If we turned left (positive), prefer left/far_left
                # If we turned right (negative), prefer right/far_right
                if self.post_recovery_bias > 0:  # Turned left
                    # Prefer left directions if they're safe
                    if safe_dirs['left']['safe']:
                        best_dir = 'left'
                        print(f"[NavController] Post-recovery bias: preferring LEFT")
                    elif safe_dirs['far_left']['safe']:
                        best_dir = 'far_left'
                        print(f"[NavController] Post-recovery bias: preferring FAR LEFT")
                else:  # Turned right
                    # Prefer right directions if they're safe
                    if safe_dirs['right']['safe']:
                        best_dir = 'right'
                        print(f"[NavController] Post-recovery bias: preferring RIGHT")
                    elif safe_dirs['far_right']['safe']:
                        best_dir = 'far_right'
                        print(f"[NavController] Post-recovery bias: preferring FAR RIGHT")
            else:
                # Bias expired - clear it
                self.post_recovery_bias = None
                self.post_recovery_time = None
                print(f"[NavController] Post-recovery bias expired - normal exploration")
        
        # Convert direction to goal angle
        direction_angles = {
            'far_left': math.radians(45),
            'left': math.radians(22.5),
            'center': 0.0,
            'right': math.radians(-22.5),
            'far_right': math.radians(-45)
        }
        
        goal_angle = self.current_heading + direction_angles.get(best_dir, 0.0)
        command = self.obstacle_avoider.compute_command(nav_data, goal_angle)
        
        # STUCK DETECTION AND RECOVERY
        
        # If we're already in recovery mode, continue it regardless of sensor data
        if self.stuck_recovery_active:
            self._execute_stuck_recovery(nav_data, 0.0)  # Duration doesn't matter once started
            return  # Stay in recovery until it completes
        
        if command.stop:
            # Emergency stop triggered
            if self.emergency_stop_time is None:
                # First time in emergency stop
                self.emergency_stop_time = time.time()
                print("[NavController] Emergency stop activated")
            else:
                # Check how long we've been stuck
                stuck_duration = time.time() - self.emergency_stop_time
                
                if stuck_duration > 1.5:  # Stuck for more than 1.5 seconds
                    # Execute recovery maneuver
                    self._execute_stuck_recovery(nav_data, stuck_duration)
                    return  # Recovery behavior handled
        else:
            # Moving normally - reset emergency stop tracking (only if not in recovery)
            if self.emergency_stop_time is not None and not self.stuck_recovery_active:
                print("[NavController] Emergency cleared, resuming normal navigation")
            self.emergency_stop_time = None
        
        # Send normal command
        self._send_velocity_command(command)
    
    def _execute_stuck_recovery(self, nav_data: Dict, stuck_duration: float):
        """Execute recovery maneuver when stuck"""
        if not self.stuck_recovery_active:
            self.stuck_recovery_active = True
            self.recovery_start_time = time.time()
            self.recovery_turn_direction = None  # Will decide turn direction
            print(f"[NavController] STUCK for {stuck_duration:.1f}s - executing recovery maneuver")
        
        recovery_time = time.time() - self.recovery_start_time
        
        # Phase 1: Back up for 2 seconds (increased from 1.5s)
        if recovery_time < 2.0:
            if recovery_time < 0.1:  # Print once
                print("[NavController] Recovery: backing up...")
            # Back up slowly
            if self.velocity_callback:
                self.velocity_callback(-0.15, 0.0)  # Negative = backward
            return
        
        # Phase 2: Turn aggressively until we find REALLY clear space
        elif recovery_time < 12.0:  # Increased max time from 9.5s to 12s
            turn_time = recovery_time - 2.0  # Subtract backup time
            
            if 0 < turn_time < 0.2:  # Print once and decide turn direction
                print("[NavController] Recovery: turning to find clear path...")
                # Decide which way to turn based on which side has more clearance
                safe_dirs = nav_data['safe_directions']
                left_clear = safe_dirs['left']['depth'] + safe_dirs['far_left']['depth']
                right_clear = safe_dirs['right']['depth'] + safe_dirs['far_right']['depth']
                self.recovery_turn_direction = 0.7 if left_clear > right_clear else -0.7
                print(f"[NavController] Recovery: turning {'LEFT' if self.recovery_turn_direction > 0 else 'RIGHT'}")
            
            # CRITICAL: Must turn for at LEAST 5 seconds (increased from 4s)
            # This ensures we rotate ~180 degrees away (5s * 0.7 rad/s = ~200 degrees)
            if turn_time < 5.0:
                # Still in mandatory turning phase - don't check for clear space yet
                if int(turn_time * 10) % 10 == 0:  # Print every second
                    print(f"[NavController] Recovery: turning... {turn_time:.1f}s / 5.0s")
                if 4.8 < turn_time < 5.0:
                    print("[NavController] Recovery: minimum turn complete, now looking for clear space...")
            else:
                # After 5s of turning, check if we found REALLY clear space
                safe_dirs = nav_data['safe_directions']
                center_clear = safe_dirs['center']['safe'] and safe_dirs['center']['depth'] > 2500  # Increased from 2000mm
                left_clear = safe_dirs['left']['safe'] and safe_dirs['left']['depth'] > 2000
                right_clear = safe_dirs['right']['safe'] and safe_dirs['right']['depth'] > 2000
                
                # Need center AND at least one side to be clear
                if center_clear and (left_clear or right_clear):
                    print(f"[NavController] Recovery: Found clear path! (center: {safe_dirs['center']['depth']:.0f}mm)")
                    # Save the direction we should prefer after recovery
                    self.post_recovery_bias = self.recovery_turn_direction
                    self.post_recovery_time = time.time()
                    # Move to phase 3
                    self.recovery_start_time = time.time() - 12.0
                    return
            
            # Keep turning in the chosen direction
            if self.velocity_callback:
                self.velocity_callback(0.0, self.recovery_turn_direction)
            return
        
        # Phase 3: Recovery complete - reset and allow normal navigation to resume
        else:
            if self.stuck_recovery_active:  # Print only once
                print("[NavController] Recovery complete - resuming exploration with bias")
                self.emergency_stop_time = None
                self.stuck_recovery_active = False
                self.recovery_start_time = None
            # Next iteration will use normal navigation with post_recovery_bias
            return
    
    def _plan_path_to_target(self):
        """Plan path from current position to target"""
        if self.target_waypoint is None:
            return
        
        print(f"[NavController] Planning path to ({self.target_waypoint.x:.2f}, {self.target_waypoint.y:.2f})")
        
        try:
            # Inflate obstacles for safety
            self.occupancy_grid.inflate_obstacles(robot_radius=0.3)
            
            # Plan path
            path = self.path_planner.plan(self.current_position, self.target_waypoint)
            
            if path.is_valid:
                self.current_path = path
                print(f"[NavController] Path planned: {len(path.waypoints)} waypoints, "
                      f"{path.total_distance:.2f}m total")
            else:
                print("[NavController] No valid path found")
                self.current_path = None
        
        except Exception as e:
            print(f"[NavController] Path planning error: {e}")
            self.current_path = None
    
    def _send_velocity_command(self, command: NavigationCommand):
        """Send velocity command to robot"""
        # Stop if commanded, but allow movement during stuck recovery
        if command.stop and not self.stuck_recovery_active:
            self._send_stop_command()
            self.is_moving = False
            return
        
        if self.velocity_callback:
            self.velocity_callback(command.linear_velocity, command.angular_velocity)
            self.is_moving = command.linear_velocity > 0 or command.angular_velocity != 0
        else:
            # No callback - just log
            if self.is_moving:
                print(f"[NavController] Command: L={command.linear_velocity:.2f} "
                      f"A={command.angular_velocity:.2f} ({command.reason})")
    
    def _send_stop_command(self):
        """Send stop command to robot"""
        if self.stop_callback:
            self.stop_callback()
        elif self.velocity_callback:
            self.velocity_callback(0.0, 0.0)
        
        self.is_moving = False
    
    def __enter__(self):
        self.start()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()


if __name__ == "__main__":
    """Test navigation controller"""
    import cv2
    
    print("="*60)
    print("OAK-D Navigation Controller Test")
    print("="*60)
    print("\nControls:")
    print("  1 - Manual mode")
    print("  2 - Assisted mode")
    print("  3 - Autonomous mode")
    print("  4 - Explore mode")
    print("  t - Set target waypoint (5m ahead)")
    print("  s - Emergency stop")
    print("  r - Reset emergency stop")
    print("  q - Quit")
    print("="*60)
    
    # Create controller
    config = DepthConfig(resolution="400p", fps=30)
    controller = NavigationController(
        depth_config=config,
        avoidance_strategy=AvoidanceStrategy.POTENTIAL_FIELD,
        update_rate=10.0
    )
    
    # Set dummy velocity callback
    def velocity_callback(linear, angular):
        print(f"[Robot] Linear: {linear:.2f} m/s, Angular: {angular:.2f} rad/s")
    
    controller.set_velocity_callback(velocity_callback)
    
    try:
        with controller:
            while True:
                # Get depth visualization
                depth_frame = controller.depth_processor.get_depth_frame()
                
                if depth_frame is not None:
                    depth_vis = controller.depth_processor.visualize_depth(depth_frame)
                    
                    if depth_vis is not None:
                        # Add state info
                        state = controller.get_state()
                        
                        y = 30
                        cv2.putText(depth_vis, f"Mode: {state.mode.value}", 
                                   (10, y), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
                        y += 25
                        cv2.putText(depth_vis, f"Moving: {state.is_moving}", 
                                   (10, y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
                        y += 20
                        cv2.putText(depth_vis, f"Obstacles: {state.obstacles_detected}", 
                                   (10, y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
                        
                        if state.target_waypoint:
                            y += 20
                            cv2.putText(depth_vis, 
                                       f"Target: ({state.target_waypoint.x:.1f}, {state.target_waypoint.y:.1f})", 
                                       (10, y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
                        
                        if state.emergency_stop:
                            cv2.putText(depth_vis, "EMERGENCY STOP", 
                                       (depth_vis.shape[1]//2 - 100, 40), 
                                       cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
                        
                        cv2.imshow("Navigation Controller", depth_vis)
                
                # Handle keyboard input
                key = cv2.waitKey(1) & 0xFF
                
                if key == ord('q'):
                    break
                elif key == ord('1'):
                    controller.set_mode(NavigationMode.MANUAL)
                elif key == ord('2'):
                    controller.set_mode(NavigationMode.ASSISTED)
                elif key == ord('3'):
                    controller.set_mode(NavigationMode.AUTONOMOUS)
                elif key == ord('4'):
                    controller.set_mode(NavigationMode.EXPLORE)
                elif key == ord('t'):
                    # Set target 5m ahead
                    target = Waypoint(
                        controller.current_position.x + 5.0 * math.cos(controller.current_heading),
                        controller.current_position.y + 5.0 * math.sin(controller.current_heading)
                    )
                    controller.set_target(target)
                elif key == ord('s'):
                    controller.emergency_stop_trigger()
                elif key == ord('r'):
                    controller.reset_emergency_stop()
    
    except KeyboardInterrupt:
        print("\nInterrupted by user")
    
    cv2.destroyAllWindows()
    print("\nTest completed")

