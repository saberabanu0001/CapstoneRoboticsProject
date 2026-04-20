#!/usr/bin/env python3
"""
Debug script to see what the depth sensor is detecting
Run this to understand why emergency stops are triggering
"""

import time
from depth_processor import DepthProcessor, DepthConfig
from obstacle_avoidance import ObstacleAvoidance, AvoidanceStrategy

def main():
    print("="*60)
    print("DEPTH SENSOR DEBUG")
    print("="*60)
    print("\nThis will show what the OAK-D camera is detecting")
    print("Press Ctrl+C to stop\n")
    
    # Configure depth processor (same as rovy_integration.py)
    config = DepthConfig(
        resolution="400p",
        fps=30,
        min_depth=400,  # 40cm
        max_depth=5000  # 5m
    )
    
    # Create processor
    processor = DepthProcessor(config)
    processor.start()
    
    # Create obstacle avoider
    avoider = ObstacleAvoidance(
        strategy=AvoidanceStrategy.POTENTIAL_FIELD,
        safe_distance=1.0,  # 1 meter
        max_speed=0.3
    )
    
    print("Camera started. Collecting data...\n")
    time.sleep(2)
    
    frame_count = 0
    
    try:
        while True:
            # Get depth frame
            depth_frame = processor.get_depth_frame()
            
            if depth_frame is not None:
                # Process for navigation
                nav_data = processor.process_depth_for_navigation(depth_frame)
                
                if nav_data and frame_count % 10 == 0:  # Print every 10 frames
                    zones = nav_data['zones']
                    obstacles = nav_data['obstacles']
                    safe_dirs = nav_data['safe_directions']
                    
                    print("\n" + "="*60)
                    print(f"Frame: {frame_count} | FPS: {processor.fps:.1f}")
                    print("="*60)
                    
                    # Show zone distances
                    print("\n📏 DISTANCE TO OBSTACLES (in millimeters):")
                    print(f"   Left:   min={zones['left']['min']:6.0f}mm  median={zones['left']['median']:6.0f}mm")
                    print(f"   Center: min={zones['center']['min']:6.0f}mm  median={zones['center']['median']:6.0f}mm")
                    print(f"   Right:  min={zones['right']['min']:6.0f}mm  median={zones['right']['median']:6.0f}mm")
                    
                    # Show obstacle detection
                    print("\n⚠️  OBSTACLE DETECTION:")
                    print(f"   Has obstacle: {obstacles['has_obstacle']}")
                    print(f"   Total coverage: {obstacles['total_percentage']:.1f}%")
                    print(f"   Left obstacles: {obstacles['left_count']}")
                    print(f"   Center obstacles: {obstacles['center_count']}")
                    print(f"   Right obstacles: {obstacles['right_count']}")
                    
                    # Show safe directions
                    print("\n🎯 SAFE DIRECTIONS:")
                    for direction in ['far_left', 'left', 'center', 'right', 'far_right']:
                        sector = safe_dirs[direction]
                        status = "✓ SAFE" if sector['safe'] else "✗ BLOCKED"
                        print(f"   {direction:10s}: {sector['depth']:6.0f}mm  {status}")
                    
                    print(f"\n   Best direction: {safe_dirs['best_direction'].upper()}")
                    
                    # Check emergency stop condition (UPDATED LOGIC)
                    print("\n🚨 EMERGENCY STOP CHECK:")
                    critical_distance = 400  # 400mm (0.4m) - critically close
                    
                    center_critically_close = zones['center']['median'] < critical_distance
                    has_safe_direction = (
                        safe_dirs['far_left']['safe'] or
                        safe_dirs['left']['safe'] or
                        safe_dirs['center']['safe'] or
                        safe_dirs['right']['safe'] or
                        safe_dirs['far_right']['safe']
                    )
                    
                    print(f"   Center critically close (< {critical_distance}mm)? {center_critically_close} (actual: {zones['center']['median']:.0f}mm)")
                    print(f"   Has safe escape direction? {has_safe_direction}")
                    
                    # Emergency stop only if blocked AND no escape
                    would_stop = center_critically_close and not has_safe_direction
                    
                    if would_stop:
                        print("   ❌ WOULD TRIGGER EMERGENCY STOP (blocked + no escape)")
                    else:
                        print("   ✅ SAFE TO MOVE")
                    
                    # Get navigation command
                    command = avoider.compute_command(nav_data, goal_direction=0.0)
                    print(f"\n🎮 NAVIGATION COMMAND:")
                    print(f"   Linear velocity: {command.linear_velocity:.2f} m/s")
                    print(f"   Angular velocity: {command.angular_velocity:.2f} rad/s")
                    print(f"   Emergency stop: {command.stop}")
                    print(f"   Reason: {command.reason}")
                
                frame_count += 1
            
            time.sleep(0.1)
    
    except KeyboardInterrupt:
        print("\n\nStopped by user")
    
    finally:
        processor.stop()
        print("\nDebug complete")


if __name__ == "__main__":
    main()

