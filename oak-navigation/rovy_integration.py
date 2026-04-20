#!/usr/bin/env python3
"""
Rovy Robot Integration with OAK-D Navigation
Connects the navigation system to actual Rovy robot motors
"""

import sys
import os
import time
import math

# Add robot directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'robot'))

from rover import Rover
from navigation_controller import NavigationController, NavigationMode
from obstacle_avoidance import AvoidanceStrategy, ObstacleAvoidance
from path_planner import Waypoint
from depth_processor import DepthConfig


class RovyNavigator:
    """
    Integration class connecting OAK-D navigation to Rovy robot
    """
    
    def __init__(self, rover_port='/dev/ttyAMA0', rover_instance=None):
        """
        Initialize Rovy navigator
        
        Args:
            rover_port: Serial port for rover connection (Pi5 uses /dev/ttyAMA0)
            rover_instance: Existing Rover instance to use (if None, creates new one)
        """
        # Initialize rover
        if rover_instance is not None:
            print("[RovyNav] Using existing Rover instance...")
            self.rover = rover_instance
            self._owns_rover = False
        else:
            print("[RovyNav] Connecting to Rovy robot...")
            self.rover = Rover(port=rover_port)
            time.sleep(0.5)
            self._owns_rover = True
        
        # Robot parameters (adjust for your Rovy)
        self.wheel_base = 0.17  # Distance between wheels in meters (17cm typical for small rovers)
        self.max_wheel_speed = 0.7  # Maximum wheel speed (from rover.py speeds)
        
        # Configure navigation
        depth_config = DepthConfig(
            resolution="400p",
            fps=30,
            min_depth=400,  # 40cm - ignore ground/chassis reflections
            max_depth=5000  # 5m (reduced for indoor use)
        )
        
        # Create obstacle avoider with safe distance
        # Using Potential Field method as researched - naturally avoids obstacles
        obstacle_avoider = ObstacleAvoidance(
            strategy=AvoidanceStrategy.POTENTIAL_FIELD,
            safe_distance=0.6,  # 60cm - typical for indoor robots
            max_speed=0.4,  # Moderate speed for exploration
            min_speed=0.15
        )
        
        # Adjust potential field parameters for better turning response
        obstacle_avoider.repulsive_gain = 3.0  # Stronger repulsion from obstacles
        obstacle_avoider.attractive_gain = 1.5  # Stronger attraction to goal
        
        # Create navigation controller
        self.nav = NavigationController(
            depth_config=depth_config,
            avoidance_strategy=AvoidanceStrategy.POTENTIAL_FIELD,
            update_rate=10.0
        )
        
        # Replace the controller's obstacle avoider with our configured one
        self.nav.obstacle_avoider = obstacle_avoider
        
        # Connect callbacks
        self.nav.set_velocity_callback(self._velocity_callback)
        self.nav.set_stop_callback(self._stop_callback)
        
        # State
        self.is_running = False
        self.total_commands = 0
        self.last_emergency_stop_print = 0
        
        print("[RovyNav] Rovy Navigator initialized!")
        print(f"  Wheel base: {self.wheel_base}m")
        print(f"  Max wheel speed: {self.max_wheel_speed}")
    
    def _velocity_callback(self, linear_vel: float, angular_vel: float):
        """
        Convert linear and angular velocities to wheel speeds
        
        Args:
            linear_vel: Forward velocity in m/s (0.0 to 0.5)
            angular_vel: Turn rate in rad/s (-1.0 to 1.0)
        """
        # Debug: Track callback invocations
        if self.total_commands % 20 == 0:
            print(f"[DEBUG] Callback called #{self.total_commands}: lin={linear_vel:.2f}, ang={angular_vel:.2f}")
        
        # Convert to wheel speeds using differential drive kinematics
        # Left wheel = V - ω * L/2
        # Right wheel = V + ω * L/2
        # where V = linear velocity, ω = angular velocity, L = wheel base
        
        left_speed = linear_vel - (angular_vel * self.wheel_base / 2.0)
        right_speed = linear_vel + (angular_vel * self.wheel_base / 2.0)
        
        # Clamp to max speed
        left_speed = max(-self.max_wheel_speed, min(self.max_wheel_speed, left_speed))
        right_speed = max(-self.max_wheel_speed, min(self.max_wheel_speed, right_speed))
        
        # Send to rover
        self.rover._send_direct(left_speed, right_speed)
        
        self.total_commands += 1
        
        # Log commands to debug why it stops
        if linear_vel != 0 or angular_vel != 0:
            print(f"[CMD] L={left_speed:.2f}, R={right_speed:.2f} (lin={linear_vel:.2f}, ang={angular_vel:.2f})")
        elif self.total_commands % 10 == 0:
            print(f"[CMD] ZERO VELOCITY (commanded {self.total_commands} times)")
    
    def _stop_callback(self):
        """Emergency stop (rate-limited printing to avoid spam during recovery)"""
        # Only print every 2 seconds to avoid spam during stuck recovery attempts
        import time
        current_time = time.time()
        if current_time - self.last_emergency_stop_print > 2.0:
            print("[RovyNav] EMERGENCY STOP")
            self.last_emergency_stop_print = current_time
        self.rover.stop()
    
    def start(self):
        """Start navigation system"""
        if self.is_running:
            print("[RovyNav] Already running")
            return
        
        print("[RovyNav] Starting navigation system...")
        self.rover.display_lines([
            "ROVY NAVIGATOR",
            "OAK-D Active",
            "Starting...",
            ""
        ])
        self.rover.lights_ctrl(0, 0)  # Lights OFF to avoid IR interference
        
        self.nav.start()
        self.is_running = True
        time.sleep(2)
        
        print("[RovyNav] Ready!")
    
    def stop(self):
        """Stop navigation system"""
        if not self.is_running:
            return
        
        print("[RovyNav] Stopping...")
        self.nav.stop()
        self.rover.stop()
        self.rover.lights_ctrl(0, 0)
        self.rover.display_lines([
            "ROVY",
            "Navigation",
            "Stopped",
            ""
        ])
        self.is_running = False
    
    def explore(self, duration: float = None):
        """
        Autonomous exploration mode - let the navigation algorithms work naturally
        
        Args:
            duration: How long to explore in seconds (None = infinite until Ctrl+C)
        """
        if duration:
            print(f"[RovyNav] Starting EXPLORE mode for {duration}s...")
        else:
            print(f"[RovyNav] Starting EXPLORE mode (infinite - Press Ctrl+C to stop)...")
        
        self.rover.display_lines([
            "ROVY",
            "EXPLORE MODE",
            "Active...",
            ""
        ])
        
        # Set to EXPLORE mode - the navigation controller will handle everything
        self.nav.set_mode(NavigationMode.EXPLORE)
        
        start_time = time.time()
        
        try:
            while True:
                # Check duration limit if set
                if duration and (time.time() - start_time >= duration):
                    print("\n[RovyNav] Duration reached")
                    break
                
                state = self.nav.get_state()
                elapsed = int(time.time() - start_time)
                
                # Print status every 5 seconds to show we're alive
                if elapsed % 5 == 0 and int(time.time()) % 5 == 0:
                    # Check if control loop is alive
                    nav_controller_running = self.nav.is_running
                    print(f"[{elapsed}s] Moving: {state.is_moving}, Obstacles: {state.obstacles_detected}, "
                          f"Commands: {self.total_commands}, ControlLoop: {nav_controller_running}")
                
                # Just monitor and display - let the navigation algorithms do their work
                # Update display every 2 seconds
                if int(time.time()) % 2 == 0:
                    if duration:
                        remaining = int(duration - elapsed)
                        time_str = f"Time: {remaining}s"
                    else:
                        time_str = f"Time: {elapsed}s"
                    
                    self.rover.display_lines([
                        "EXPLORE MODE",
                        time_str,
                        f"Moving: {state.is_moving}",
                        f"Obstacle: {state.obstacles_detected}"
                    ])
                
                time.sleep(0.5)
        
        except KeyboardInterrupt:
            print("\n[RovyNav] Interrupted by user")
        
        finally:
            self.nav.set_mode(NavigationMode.MANUAL)
            self.rover.stop()
            print("[RovyNav] Exploration complete")
    
    def navigate_to(self, x: float, y: float):
        """
        Navigate to specific coordinate
        
        Args:
            x, y: Target position in meters
        """
        target = Waypoint(x, y)
        
        print(f"[RovyNav] Navigating to ({x:.1f}, {y:.1f})")
        self.rover.display_lines([
            "NAVIGATE MODE",
            f"Target: {x:.1f},{y:.1f}",
            "Planning...",
            ""
        ])
        
        self.nav.set_mode(NavigationMode.AUTONOMOUS)
        self.nav.set_target(target)
        
        try:
            while True:
                state = self.nav.get_state()
                
                if state.target_waypoint is None:
                    print("[RovyNav] Target reached!")
                    self.rover.display_lines([
                        "NAVIGATE MODE",
                        "TARGET",
                        "REACHED!",
                        ""
                    ])
                    break
                
                # Update display
                if state.current_position and state.target_waypoint:
                    dist = state.current_position.distance_to(state.target_waypoint)
                    self.rover.display_lines([
                        "NAVIGATE MODE",
                        f"Dist: {dist:.1f}m",
                        f"Moving: {state.is_moving}",
                        f"Obs: {state.obstacles_detected}"
                    ])
                
                time.sleep(0.5)
        
        except KeyboardInterrupt:
            print("\n[RovyNav] Interrupted")
        
        finally:
            self.nav.set_mode(NavigationMode.MANUAL)
            self.rover.stop()
    
    def get_status(self):
        """Get rover and navigation status"""
        rover_status = self.rover.get_status()
        nav_state = self.nav.get_state()
        
        return {
            'rover': rover_status,
            'navigation': {
                'mode': nav_state.mode.value,
                'is_moving': nav_state.is_moving,
                'obstacles_detected': nav_state.obstacles_detected,
                'emergency_stop': nav_state.emergency_stop
            }
        }
    
    def cleanup(self):
        """Clean up resources"""
        self.stop()
        # Only cleanup rover if we created it
        if self._owns_rover:
            self.rover.cleanup()
        print("[RovyNav] Cleaned up")


def main():
    """Demo program"""
    print("="*60)
    print("ROVY OAK-D NAVIGATION DEMO")
    print("="*60)
    print("\nThis will make your Rovy robot move autonomously!")
    print("Make sure:")
    print("  1. Robot is on the ground (not on a table)")
    print("  2. There's clear space around it")
    print("  3. You're ready to grab it if needed")
    print()
    
    input("Press ENTER to start (Ctrl+C to abort)...")
    
    try:
        # Create navigator
        navigator = RovyNavigator(rover_port='/dev/ttyAMA0')
        
        # Start navigation system
        navigator.start()
        
        # Show status
        status = navigator.get_status()
        print(f"\n[Status]")
        print(f"  Battery: {status['rover'].get('voltage', 0):.1f}V")
        print(f"  Navigation: {status['navigation']['mode']}")
        print()
        
        # Run exploration
        print("Starting continuous exploration...")
        print("Robot will move and avoid obstacles autonomously")
        print("When blocked, it will turn to explore other directions")
        print("Press Ctrl+C to stop\n")
        
        navigator.explore(duration=None)  # Run indefinitely until Ctrl+C
        
        print("\n" + "="*60)
        print("Demo complete!")
        print("="*60)
        
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
    
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        if 'navigator' in locals():
            navigator.cleanup()


if __name__ == "__main__":
    main()

