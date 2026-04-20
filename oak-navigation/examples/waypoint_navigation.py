#!/usr/bin/env python3
"""
Waypoint Navigation Example
Navigate through a series of waypoints
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from navigation_controller import NavigationController, NavigationMode
from path_planner import Waypoint
from obstacle_avoidance import AvoidanceStrategy
import time


def main():
    print("="*60)
    print("Waypoint Navigation Example")
    print("="*60)
    
    # Create controller
    controller = NavigationController(
        avoidance_strategy=AvoidanceStrategy.POTENTIAL_FIELD,
        update_rate=10.0
    )
    
    # Motor control callback
    def velocity_callback(linear, angular):
        print(f"[Motors] L={linear:.2f}, A={angular:.2f}")
        # TODO: Send to your robot
    
    controller.set_velocity_callback(velocity_callback)
    
    # Define waypoints (square pattern)
    waypoints = [
        Waypoint(12.0, 10.0),  # Start at center
        Waypoint(15.0, 10.0),  # Move right 3m
        Waypoint(15.0, 13.0),  # Move forward 3m
        Waypoint(12.0, 13.0),  # Move left 3m
        Waypoint(12.0, 10.0),  # Return to start
    ]
    
    print(f"\nWaypoints to visit:")
    for i, wp in enumerate(waypoints, 1):
        print(f"  {i}. ({wp.x:.1f}, {wp.y:.1f})")
    
    # Start navigation
    controller.start()
    
    try:
        time.sleep(2.0)
        
        # Set waypoint mode
        controller.set_mode(NavigationMode.WAYPOINT)
        
        # Add waypoints
        for wp in waypoints:
            controller.add_waypoint(wp)
        
        print("\nNavigating through waypoints...")
        print("Press Ctrl+C to stop\n")
        
        # Monitor progress
        last_target = None
        while True:
            state = controller.get_state()
            
            # Check if target changed (reached waypoint)
            if state.target_waypoint != last_target:
                if state.target_waypoint:
                    print(f"\n→ Heading to waypoint: "
                          f"({state.target_waypoint.x:.1f}, {state.target_waypoint.y:.1f})")
                else:
                    print("\n✓ All waypoints reached!")
                    break
                last_target = state.target_waypoint
            
            # Show status
            if state.target_waypoint:
                dist = state.current_position.distance_to(state.target_waypoint)
                print(f"\rDistance to target: {dist:.2f}m | "
                      f"Moving: {state.is_moving} | "
                      f"Obstacles: {state.obstacles_detected}  ",
                      end='', flush=True)
            
            time.sleep(0.5)
        
        print("\n\nMission complete!")
        
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
    
    finally:
        controller.stop()
    
    print("\n" + "="*60)


if __name__ == "__main__":
    main()

