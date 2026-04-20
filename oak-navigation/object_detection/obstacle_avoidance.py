#!/usr/bin/env python3
"""
Obstacle Avoidance Module for OAK-D Navigation
Implements various obstacle avoidance algorithms
"""

import numpy as np
from typing import Tuple, Dict, List, Optional
from enum import Enum
from dataclasses import dataclass
import math


class AvoidanceStrategy(Enum):
    """Different obstacle avoidance strategies"""
    POTENTIAL_FIELD = "potential_field"  # Artificial potential field method
    VFH = "vector_field_histogram"  # Vector Field Histogram
    SIMPLE_REACTIVE = "simple_reactive"  # Simple reactive behavior
    WALL_FOLLOWING = "wall_following"  # Follow walls


@dataclass
class NavigationCommand:
    """Command output from obstacle avoidance"""
    linear_velocity: float  # Forward speed (-1.0 to 1.0)
    angular_velocity: float  # Turn rate (-1.0 to 1.0, negative = left)
    stop: bool  # Emergency stop
    confidence: float  # Confidence in this command (0-1)
    reason: str  # Human-readable reason for decision


class ObstacleAvoidance:
    """
    Obstacle avoidance controller using depth data
    """
    
    def __init__(self, 
                 strategy: AvoidanceStrategy = AvoidanceStrategy.POTENTIAL_FIELD,
                 safe_distance: float = 1.5,  # meters
                 max_speed: float = 0.5,  # m/s
                 min_speed: float = 0.1):
        """
        Initialize obstacle avoidance
        
        Args:
            strategy: Avoidance algorithm to use
            safe_distance: Minimum safe distance from obstacles (meters)
            max_speed: Maximum linear velocity
            min_speed: Minimum linear velocity when moving
        """
        self.strategy = strategy
        self.safe_distance = safe_distance * 1000  # Convert to mm
        self.max_speed = max_speed
        self.min_speed = min_speed
        
        # Potential field parameters
        self.attractive_gain = 1.0
        self.repulsive_gain = 2.0
        self.repulsive_range = self.safe_distance * 2
        
        # VFH parameters
        self.vfh_threshold = 100  # Obstacle density threshold
        self.vfh_sectors = 72  # Number of angular sectors (5° each)
        
        # State
        self.last_command = None
        self.stuck_counter = 0
        self.last_turn_direction = 1  # 1 = right, -1 = left
        
    def compute_command(self, 
                       nav_data: Dict,
                       goal_direction: Optional[float] = None) -> NavigationCommand:
        """
        Compute navigation command based on depth data
        
        Args:
            nav_data: Navigation data from depth processor
            goal_direction: Desired heading in radians (0 = forward, None = explore)
            
        Returns:
            NavigationCommand with velocity commands
        """
        if nav_data is None:
            return NavigationCommand(0.0, 0.0, True, 0.0, "No depth data")
        
        # Check for emergency stop conditions
        if self._check_emergency_stop(nav_data):
            return NavigationCommand(0.0, 0.0, True, 1.0, "Emergency stop - obstacle too close")
        
        # Route to appropriate strategy
        if self.strategy == AvoidanceStrategy.POTENTIAL_FIELD:
            return self._potential_field_method(nav_data, goal_direction)
        elif self.strategy == AvoidanceStrategy.VFH:
            return self._vfh_method(nav_data, goal_direction)
        elif self.strategy == AvoidanceStrategy.SIMPLE_REACTIVE:
            return self._simple_reactive_method(nav_data, goal_direction)
        elif self.strategy == AvoidanceStrategy.WALL_FOLLOWING:
            return self._wall_following_method(nav_data)
        else:
            return self._simple_reactive_method(nav_data, goal_direction)
    
    def _check_emergency_stop(self, nav_data: Dict) -> bool:
        """
        Check if emergency stop is needed
        
        Emergency stop only if:
        1. Something very close in center (< 400mm / 0.4m)
        2. AND no safe escape directions available
        """
        zones = nav_data['zones']
        safe_dirs = nav_data['safe_directions']
        
        # Critical distance: 400mm (0.4m) - anything closer is too dangerous
        critical_distance = 400  # mm
        
        # Check if something is critically close in center
        center_clear = zones['center']['median'] > critical_distance
        
        # Check if we have ANY safe direction to move/turn
        has_safe_direction = (
            safe_dirs['far_left']['safe'] or
            safe_dirs['left']['safe'] or
            safe_dirs['center']['safe'] or
            safe_dirs['right']['safe'] or
            safe_dirs['far_right']['safe']
        )
        
        # Emergency stop only if center is blocked AND no escape routes
        if not center_clear and not has_safe_direction:
            return True
        
        return False
    
    def _potential_field_method(self, 
                                nav_data: Dict, 
                                goal_direction: Optional[float]) -> NavigationCommand:
        """
        Artificial Potential Field method
        Goal creates attractive force, obstacles create repulsive forces
        """
        zones = nav_data['zones']
        safe_dirs = nav_data['safe_directions']
        
        # Initialize forces
        attractive_force = np.array([0.0, 0.0])
        repulsive_force = np.array([0.0, 0.0])
        
        # Attractive force toward goal
        if goal_direction is not None:
            attractive_force = self.attractive_gain * np.array([
                math.cos(goal_direction),
                math.sin(goal_direction)
            ])
        else:
            # No goal - just move forward
            attractive_force = self.attractive_gain * np.array([1.0, 0.0])
        
        # Repulsive forces from obstacles
        # Analyze each sector
        sector_angles = {
            'far_left': math.radians(45),
            'left': math.radians(22.5),
            'center': 0.0,
            'right': math.radians(-22.5),
            'far_right': math.radians(-45)
        }
        
        for sector_name, angle in sector_angles.items():
            sector = safe_dirs[sector_name]
            distance = sector['depth']
            
            if distance < self.repulsive_range:
                # Calculate repulsive force magnitude
                force_magnitude = self.repulsive_gain * (
                    1.0 / distance - 1.0 / self.repulsive_range
                ) * (1.0 / (distance ** 2))
                
                # Force direction is away from obstacle
                force_direction = np.array([
                    -math.cos(angle),
                    -math.sin(angle)
                ])
                
                repulsive_force += force_magnitude * force_direction
        
        # Combine forces
        total_force = attractive_force + repulsive_force
        
        # Convert to velocity commands
        force_magnitude = np.linalg.norm(total_force)
        if force_magnitude < 0.01:
            # Stuck - try random turn
            return self._unstuck_maneuver()
        
        # Normalize and scale
        force_normalized = total_force / force_magnitude
        
        # Linear velocity based on forward component and obstacles
        forward_component = force_normalized[0]
        linear_vel = self.max_speed * max(0.0, forward_component)
        
        # Reduce speed if obstacles nearby
        min_distance = min(
            zones['left']['median'],
            zones['center']['median'],
            zones['right']['median']
        )
        
        if min_distance < self.safe_distance * 1.5:
            speed_factor = min_distance / (self.safe_distance * 1.5)
            linear_vel *= speed_factor
        
        # Ensure minimum speed if moving
        if linear_vel > 0:
            linear_vel = max(linear_vel, self.min_speed)
        
        # Angular velocity based on lateral component
        lateral_component = force_normalized[1]
        angular_vel = lateral_component * 1.0  # Scale to reasonable turn rate
        
        # Clamp values
        linear_vel = np.clip(linear_vel, 0.0, self.max_speed)
        angular_vel = np.clip(angular_vel, -1.0, 1.0)
        
        confidence = min(1.0, force_magnitude / 2.0)
        reason = f"Potential field: L={linear_vel:.2f} A={angular_vel:.2f}"
        
        return NavigationCommand(linear_vel, angular_vel, False, confidence, reason)
    
    def _vfh_method(self, nav_data: Dict, goal_direction: Optional[float]) -> NavigationCommand:
        """
        Vector Field Histogram method
        Creates polar histogram of obstacles and finds best gap
        """
        grid_depth = nav_data['grid_depth']
        
        # Create polar histogram
        histogram = self._create_polar_histogram(grid_depth)
        
        # Find candidate directions (valleys in histogram)
        candidates = self._find_candidate_directions(histogram)
        
        if len(candidates) == 0:
            return self._unstuck_maneuver()
        
        # Select best candidate based on goal
        if goal_direction is not None:
            best_direction = self._select_best_direction(candidates, goal_direction)
        else:
            # No goal - prefer forward direction
            best_direction = self._select_best_direction(candidates, 0.0)
        
        # Convert to velocity commands
        angular_vel = best_direction / math.pi  # Normalize to -1 to 1
        
        # Linear velocity based on obstacle proximity
        zones = nav_data['zones']
        min_distance = zones['center']['median']
        
        if min_distance > self.safe_distance * 2:
            linear_vel = self.max_speed
        elif min_distance > self.safe_distance:
            linear_vel = self.max_speed * 0.7
        else:
            linear_vel = self.min_speed
        
        # Reduce speed when turning
        linear_vel *= (1.0 - abs(angular_vel) * 0.5)
        
        confidence = 0.8
        reason = f"VFH: direction={math.degrees(best_direction):.0f}°"
        
        return NavigationCommand(linear_vel, angular_vel, False, confidence, reason)
    
    def _simple_reactive_method(self, 
                               nav_data: Dict, 
                               goal_direction: Optional[float]) -> NavigationCommand:
        """
        Simple reactive obstacle avoidance
        Turn away from obstacles, move toward clear space
        """
        zones = nav_data['zones']
        safe_dirs = nav_data['safe_directions']
        obstacles = nav_data['obstacles']
        
        # Get best direction
        best_dir = safe_dirs['best_direction']
        
        # Map direction to angular velocity
        direction_map = {
            'far_left': 0.8,
            'left': 0.4,
            'center': 0.0,
            'right': -0.4,
            'far_right': -0.8
        }
        
        angular_vel = direction_map.get(best_dir, 0.0)
        
        # Determine linear velocity based on center clearance
        center_distance = zones['center']['median']
        
        if center_distance > self.safe_distance * 2:
            linear_vel = self.max_speed
            reason = "Clear ahead - full speed"
        elif center_distance > self.safe_distance:
            linear_vel = self.max_speed * 0.6
            reason = "Moderate clearance - reduced speed"
        elif center_distance > self.safe_distance * 0.7:
            linear_vel = self.min_speed
            reason = "Close obstacle - slow speed"
        else:
            linear_vel = 0.0
            angular_vel = 0.5 if angular_vel >= 0 else -0.5
            reason = "Too close - turn in place"
        
        # If turning, reduce forward speed
        if abs(angular_vel) > 0.3:
            linear_vel *= 0.5
        
        confidence = 0.7 if best_dir == 'center' else 0.5
        
        return NavigationCommand(linear_vel, angular_vel, False, confidence, reason)
    
    def _wall_following_method(self, nav_data: Dict) -> NavigationCommand:
        """
        Wall following behavior
        Maintains constant distance from wall on one side
        """
        zones = nav_data['zones']
        
        # Choose which side to follow (prefer right wall)
        follow_right = True
        wall_distance = zones['right']['median'] if follow_right else zones['left']['median']
        
        # Desired wall distance
        desired_distance = self.safe_distance * 1.2
        
        # Calculate error
        distance_error = wall_distance - desired_distance
        
        # Proportional control for angular velocity
        kp = 0.001  # Proportional gain
        angular_vel = -kp * distance_error if follow_right else kp * distance_error
        angular_vel = np.clip(angular_vel, -0.5, 0.5)
        
        # Linear velocity based on front clearance
        front_distance = zones['center']['median']
        if front_distance > self.safe_distance * 2:
            linear_vel = self.max_speed * 0.7
        elif front_distance > self.safe_distance:
            linear_vel = self.max_speed * 0.4
        else:
            # Wall ahead - turn away from wall
            linear_vel = 0.0
            angular_vel = -0.7 if follow_right else 0.7
        
        reason = f"Wall following: dist={wall_distance:.0f}mm"
        
        return NavigationCommand(linear_vel, angular_vel, False, 0.6, reason)
    
    def _unstuck_maneuver(self) -> NavigationCommand:
        """Execute maneuver to get unstuck"""
        self.stuck_counter += 1
        
        if self.stuck_counter % 2 == 0:
            # Alternate turn direction
            self.last_turn_direction *= -1
        
        # Turn in place
        angular_vel = 0.6 * self.last_turn_direction
        
        return NavigationCommand(
            0.0, angular_vel, False, 0.3, 
            f"Unstuck maneuver #{self.stuck_counter}"
        )
    
    def _create_polar_histogram(self, grid_depth: np.ndarray) -> np.ndarray:
        """Create polar histogram from depth grid"""
        grid_h, grid_w = grid_depth.shape
        histogram = np.zeros(self.vfh_sectors)
        
        # Convert grid to polar coordinates and accumulate
        center_y, center_x = grid_h // 2, grid_w // 2
        
        for i in range(grid_h):
            for j in range(grid_w):
                depth = grid_depth[i, j]
                
                # Calculate angle from center
                dy = i - center_y
                dx = j - center_x
                angle = math.atan2(dy, dx)
                
                # Map to sector
                sector = int((angle + math.pi) / (2 * math.pi) * self.vfh_sectors)
                sector = np.clip(sector, 0, self.vfh_sectors - 1)
                
                # Add obstacle density (inverse of depth)
                if depth > 0:
                    density = 1000.0 / max(depth, 100)  # Avoid division by zero
                    histogram[sector] += density
        
        return histogram
    
    def _find_candidate_directions(self, histogram: np.ndarray) -> List[float]:
        """Find candidate directions (valleys in histogram)"""
        candidates = []
        
        # Find sectors below threshold
        for i in range(len(histogram)):
            if histogram[i] < self.vfh_threshold:
                # Convert sector to angle
                angle = (i / self.vfh_sectors) * 2 * math.pi - math.pi
                candidates.append(angle)
        
        return candidates
    
    def _select_best_direction(self, 
                              candidates: List[float], 
                              goal_direction: float) -> float:
        """Select best direction from candidates based on goal"""
        if len(candidates) == 0:
            return 0.0
        
        # Find candidate closest to goal direction
        best_candidate = min(candidates, 
                            key=lambda c: abs(self._angle_diff(c, goal_direction)))
        
        return best_candidate
    
    def _angle_diff(self, angle1: float, angle2: float) -> float:
        """Calculate smallest difference between two angles"""
        diff = angle1 - angle2
        while diff > math.pi:
            diff -= 2 * math.pi
        while diff < -math.pi:
            diff += 2 * math.pi
        return diff


if __name__ == "__main__":
    """Test obstacle avoidance with simulated data"""
    print("Testing Obstacle Avoidance Module")
    
    # Create simulated navigation data
    def create_test_data(scenario: str) -> Dict:
        """Create test scenarios"""
        if scenario == "clear":
            return {
                'zones': {
                    'left': {'median': 3000, 'min': 2500},
                    'center': {'median': 5000, 'min': 4000},
                    'right': {'median': 3000, 'min': 2500}
                },
                'obstacles': {'total_percentage': 5.0},
                'safe_directions': {
                    'far_left': {'depth': 3000, 'safe': True},
                    'left': {'depth': 3500, 'safe': True},
                    'center': {'depth': 5000, 'safe': True},
                    'right': {'depth': 3500, 'safe': True},
                    'far_right': {'depth': 3000, 'safe': True},
                    'best_direction': 'center'
                },
                'grid_depth': np.ones((48, 64)) * 4000
            }
        elif scenario == "obstacle_ahead":
            return {
                'zones': {
                    'left': {'median': 3000, 'min': 2500},
                    'center': {'median': 800, 'min': 700},
                    'right': {'median': 3000, 'min': 2500}
                },
                'obstacles': {'total_percentage': 25.0},
                'safe_directions': {
                    'far_left': {'depth': 3000, 'safe': True},
                    'left': {'depth': 3500, 'safe': True},
                    'center': {'depth': 800, 'safe': False},
                    'right': {'depth': 3500, 'safe': True},
                    'far_right': {'depth': 3000, 'safe': True},
                    'best_direction': 'right'
                },
                'grid_depth': np.ones((48, 64)) * 3000
            }
        else:  # "emergency"
            return {
                'zones': {
                    'left': {'median': 600, 'min': 500},
                    'center': {'median': 400, 'min': 300},
                    'right': {'median': 600, 'min': 500}
                },
                'obstacles': {'total_percentage': 60.0},
                'safe_directions': {
                    'far_left': {'depth': 700, 'safe': False},
                    'left': {'depth': 600, 'safe': False},
                    'center': {'depth': 400, 'safe': False},
                    'right': {'depth': 600, 'safe': False},
                    'far_right': {'depth': 700, 'safe': False},
                    'best_direction': 'far_left'
                },
                'grid_depth': np.ones((48, 64)) * 500
            }
    
    # Test different strategies
    strategies = [
        AvoidanceStrategy.SIMPLE_REACTIVE,
        AvoidanceStrategy.POTENTIAL_FIELD,
        AvoidanceStrategy.WALL_FOLLOWING
    ]
    
    scenarios = ["clear", "obstacle_ahead", "emergency"]
    
    for strategy in strategies:
        print(f"\n{'='*60}")
        print(f"Testing {strategy.value}")
        print('='*60)
        
        avoider = ObstacleAvoidance(strategy=strategy, safe_distance=1.5)
        
        for scenario in scenarios:
            test_data = create_test_data(scenario)
            command = avoider.compute_command(test_data, goal_direction=0.0)
            
            print(f"\nScenario: {scenario}")
            print(f"  Linear velocity: {command.linear_velocity:.2f}")
            print(f"  Angular velocity: {command.angular_velocity:.2f}")
            print(f"  Stop: {command.stop}")
            print(f"  Confidence: {command.confidence:.2f}")
            print(f"  Reason: {command.reason}")
    
    print("\n" + "="*60)
    print("Test completed")

