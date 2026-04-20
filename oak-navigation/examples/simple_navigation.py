#!/usr/bin/env python3
"""
Simple Navigation Example
Demonstrates basic autonomous navigation using OAK-D
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from navigation_controller import NavigationController, NavigationMode
from obstacle_avoidance import AvoidanceStrategy
from path_planner import PlannerType
from depth_processor import DepthConfig
import time


def main():
    print("="*60)
    print("Simple OAK-D Navigation Example")
    print("="*60)
    
    # Configure depth processor
    depth_config = DepthConfig(
        resolution="400p",
        fps=30,
        min_depth=300,
        max_depth=5000
    )
    
    # Create navigation controller
    controller = NavigationController(
        depth_config=depth_config,
        avoidance_strategy=AvoidanceStrategy.POTENTIAL_FIELD,
        planner_type=PlannerType.ASTAR,
        update_rate=10.0
    )
    
    # Set up motor control callback
    def velocity_callback(linear, angular):
        """Send velocity commands to your robot"""
        print(f"[Motors] Linear: {linear:.2f} m/s, Angular: {angular:.2f} rad/s")
        # TODO: Replace with your actual motor control code
        # Example:
        # robot.set_velocity(linear, angular)
    
    controller.set_velocity_callback(velocity_callback)
    
    # Start navigation
    print("\nStarting navigation controller...")
    controller.start()
    
    try:
        # Wait for initialization
        time.sleep(2.0)
        
        # Set to explore mode
        print("\nEntering EXPLORE mode...")
        controller.set_mode(NavigationMode.EXPLORE)
        
        # Run for 30 seconds
        print("Exploring for 30 seconds...")
        print("Robot will autonomously navigate and avoid obstacles")
        
        for i in range(30):
            state = controller.get_state()
            print(f"\r[{i+1}/30s] Mode: {state.mode.value}, "
                  f"Moving: {state.is_moving}, "
                  f"Obstacles: {state.obstacles_detected}", 
                  end='', flush=True)
            time.sleep(1.0)
        
        print("\n\nStopping navigation...")
        controller.set_mode(NavigationMode.MANUAL)
        
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
    
    finally:
        controller.stop()
        print("Navigation stopped")
    
    print("\n" + "="*60)
    print("Example completed")
    print("="*60)


if __name__ == "__main__":
    main()

