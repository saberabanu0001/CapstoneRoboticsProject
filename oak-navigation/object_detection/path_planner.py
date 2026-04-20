#!/usr/bin/env python3
"""
Path Planning Module for OAK-D Navigation
Implements A* and other path planning algorithms
"""

import numpy as np
from typing import List, Tuple, Optional, Dict, Set
from dataclasses import dataclass
import heapq
import math
from enum import Enum


class PlannerType(Enum):
    """Available path planning algorithms"""
    ASTAR = "astar"
    DIJKSTRA = "dijkstra"
    RRT = "rrt"  # Rapidly-exploring Random Tree
    POTENTIAL_FIELD = "potential_field"


@dataclass
class Waypoint:
    """A waypoint in the path"""
    x: float  # meters
    y: float  # meters
    heading: Optional[float] = None  # radians
    
    def distance_to(self, other: 'Waypoint') -> float:
        """Calculate Euclidean distance to another waypoint"""
        return math.sqrt((self.x - other.x)**2 + (self.y - other.y)**2)
    
    def __hash__(self):
        return hash((round(self.x, 2), round(self.y, 2)))
    
    def __eq__(self, other):
        if not isinstance(other, Waypoint):
            return False
        return (round(self.x, 2) == round(other.x, 2) and 
                round(self.y, 2) == round(other.y, 2))


@dataclass
class Path:
    """A planned path"""
    waypoints: List[Waypoint]
    total_distance: float
    is_valid: bool
    planner_used: str
    
    def get_next_waypoint(self, current_pos: Waypoint, 
                         lookahead_distance: float = 0.5) -> Optional[Waypoint]:
        """Get next waypoint based on lookahead distance"""
        if not self.waypoints:
            return None
        
        # Find closest waypoint ahead
        for wp in self.waypoints:
            dist = current_pos.distance_to(wp)
            if dist >= lookahead_distance:
                return wp
        
        # Return last waypoint if all are closer
        return self.waypoints[-1] if self.waypoints else None


class OccupancyGrid:
    """2D occupancy grid for path planning"""
    
    def __init__(self, width: float, height: float, resolution: float = 0.1):
        """
        Initialize occupancy grid
        
        Args:
            width: Grid width in meters
            height: Grid height in meters
            resolution: Grid cell size in meters
        """
        self.width = width
        self.height = height
        self.resolution = resolution
        
        self.grid_width = int(width / resolution)
        self.grid_height = int(height / resolution)
        
        # Grid: 0 = free, 1 = occupied, -1 = unknown
        self.grid = np.zeros((self.grid_height, self.grid_width), dtype=np.int8)
        
        # Robot position (center of grid initially)
        self.robot_x = width / 2
        self.robot_y = height / 2
        self.robot_heading = 0.0  # radians
    
    def world_to_grid(self, x: float, y: float) -> Tuple[int, int]:
        """Convert world coordinates to grid indices"""
        grid_x = int(x / self.resolution)
        grid_y = int(y / self.resolution)
        return grid_x, grid_y
    
    def grid_to_world(self, grid_x: int, grid_y: int) -> Tuple[float, float]:
        """Convert grid indices to world coordinates"""
        x = (grid_x + 0.5) * self.resolution
        y = (grid_y + 0.5) * self.resolution
        return x, y
    
    def is_valid_cell(self, grid_x: int, grid_y: int) -> bool:
        """Check if grid cell is within bounds"""
        return (0 <= grid_x < self.grid_width and 
                0 <= grid_y < self.grid_height)
    
    def is_occupied(self, grid_x: int, grid_y: int) -> bool:
        """Check if grid cell is occupied"""
        if not self.is_valid_cell(grid_x, grid_y):
            return True  # Out of bounds = occupied
        return self.grid[grid_y, grid_x] > 0
    
    def set_occupied(self, grid_x: int, grid_y: int, occupied: bool = True):
        """Mark grid cell as occupied or free"""
        if self.is_valid_cell(grid_x, grid_y):
            self.grid[grid_y, grid_x] = 1 if occupied else 0
    
    def update_from_depth(self, nav_data: Dict, robot_pos: Tuple[float, float, float]):
        """
        Update occupancy grid from depth sensor data
        
        Args:
            nav_data: Navigation data from depth processor
            robot_pos: (x, y, heading) of robot in world coordinates
        """
        self.robot_x, self.robot_y, self.robot_heading = robot_pos
        
        grid_depth = nav_data.get('grid_depth')
        if grid_depth is None:
            return
        
        # Convert depth grid to occupancy
        grid_h, grid_w = grid_depth.shape
        
        # Camera FOV (approximate for OAK-D Lite)
        hfov = math.radians(73)  # Horizontal field of view
        
        for i in range(grid_h):
            for j in range(grid_w):
                depth_mm = grid_depth[i, j]
                
                if depth_mm <= 0:
                    continue
                
                depth_m = depth_mm / 1000.0
                
                # Calculate angle relative to robot heading
                # Map grid column to angle
                angle_offset = (j / grid_w - 0.5) * hfov
                angle = self.robot_heading + angle_offset
                
                # Calculate world position of this depth point
                world_x = self.robot_x + depth_m * math.cos(angle)
                world_y = self.robot_y + depth_m * math.sin(angle)
                
                # Convert to grid coordinates
                grid_x, grid_y = self.world_to_grid(world_x, world_y)
                
                # Mark as occupied if close enough
                if depth_m < 2.0:  # Within 2 meters
                    self.set_occupied(grid_x, grid_y, occupied=True)
                elif depth_m < 5.0:  # Mark as free if farther
                    # Ray trace from robot to this point and mark as free
                    self._ray_trace_free(self.robot_x, self.robot_y, world_x, world_y)
    
    def _ray_trace_free(self, x0: float, y0: float, x1: float, y1: float):
        """Mark cells along ray as free (Bresenham's algorithm)"""
        gx0, gy0 = self.world_to_grid(x0, y0)
        gx1, gy1 = self.world_to_grid(x1, y1)
        
        dx = abs(gx1 - gx0)
        dy = abs(gy1 - gy0)
        sx = 1 if gx0 < gx1 else -1
        sy = 1 if gy0 < gy1 else -1
        err = dx - dy
        
        x, y = gx0, gy0
        
        while True:
            if self.is_valid_cell(x, y):
                # Don't overwrite occupied cells
                if self.grid[y, x] != 1:
                    self.grid[y, x] = 0
            
            if x == gx1 and y == gy1:
                break
            
            e2 = 2 * err
            if e2 > -dy:
                err -= dy
                x += sx
            if e2 < dx:
                err += dx
                y += sy
    
    def inflate_obstacles(self, robot_radius: float = 0.3):
        """Inflate obstacles by robot radius for safety"""
        inflation_cells = int(robot_radius / self.resolution)
        
        # Create copy of grid
        inflated = self.grid.copy()
        
        # Inflate each occupied cell
        for i in range(self.grid_height):
            for j in range(self.grid_width):
                if self.grid[i, j] > 0:
                    # Inflate in all directions
                    for di in range(-inflation_cells, inflation_cells + 1):
                        for dj in range(-inflation_cells, inflation_cells + 1):
                            ni, nj = i + di, j + dj
                            if self.is_valid_cell(nj, ni):
                                # Check if within circular radius
                                if math.sqrt(di**2 + dj**2) <= inflation_cells:
                                    inflated[ni, nj] = 1
        
        self.grid = inflated
    
    def get_visualization(self) -> np.ndarray:
        """Get RGB visualization of grid"""
        vis = np.zeros((self.grid_height, self.grid_width, 3), dtype=np.uint8)
        
        # Free = white, occupied = black, unknown = gray
        vis[self.grid == 0] = [255, 255, 255]  # Free
        vis[self.grid == 1] = [0, 0, 0]  # Occupied
        vis[self.grid == -1] = [128, 128, 128]  # Unknown
        
        # Mark robot position
        robot_gx, robot_gy = self.world_to_grid(self.robot_x, self.robot_y)
        if self.is_valid_cell(robot_gx, robot_gy):
            # Draw robot as red circle
            for di in range(-2, 3):
                for dj in range(-2, 3):
                    if math.sqrt(di**2 + dj**2) <= 2:
                        ni, nj = robot_gy + di, robot_gx + dj
                        if self.is_valid_cell(nj, ni):
                            vis[ni, nj] = [0, 0, 255]  # Red
        
        return vis


class PathPlanner:
    """Path planning using various algorithms"""
    
    def __init__(self, 
                 planner_type: PlannerType = PlannerType.ASTAR,
                 occupancy_grid: Optional[OccupancyGrid] = None):
        """
        Initialize path planner
        
        Args:
            planner_type: Algorithm to use
            occupancy_grid: Occupancy grid for planning
        """
        self.planner_type = planner_type
        self.grid = occupancy_grid or OccupancyGrid(10.0, 10.0, 0.1)
        
    def plan(self, start: Waypoint, goal: Waypoint) -> Path:
        """
        Plan path from start to goal
        
        Args:
            start: Starting waypoint
            goal: Goal waypoint
            
        Returns:
            Planned path
        """
        if self.planner_type == PlannerType.ASTAR:
            return self._plan_astar(start, goal)
        elif self.planner_type == PlannerType.DIJKSTRA:
            return self._plan_dijkstra(start, goal)
        elif self.planner_type == PlannerType.RRT:
            return self._plan_rrt(start, goal)
        else:
            return Path([], 0.0, False, "unknown")
    
    def _plan_astar(self, start: Waypoint, goal: Waypoint) -> Path:
        """A* path planning algorithm"""
        start_grid = self.grid.world_to_grid(start.x, start.y)
        goal_grid = self.grid.world_to_grid(goal.x, goal.y)
        
        # Check if start or goal is occupied
        if self.grid.is_occupied(*start_grid) or self.grid.is_occupied(*goal_grid):
            return Path([], 0.0, False, "astar")
        
        # A* implementation
        open_set = []
        heapq.heappush(open_set, (0, start_grid))
        
        came_from = {}
        g_score = {start_grid: 0}
        f_score = {start_grid: self._heuristic(start_grid, goal_grid)}
        
        while open_set:
            _, current = heapq.heappop(open_set)
            
            if current == goal_grid:
                # Reconstruct path
                return self._reconstruct_path(came_from, current, start_grid)
            
            # Check neighbors (8-connected)
            for dx, dy in [(-1,-1), (-1,0), (-1,1), (0,-1), (0,1), (1,-1), (1,0), (1,1)]:
                neighbor = (current[0] + dx, current[1] + dy)
                
                if not self.grid.is_valid_cell(*neighbor):
                    continue
                
                if self.grid.is_occupied(*neighbor):
                    continue
                
                # Calculate tentative g_score
                move_cost = math.sqrt(dx**2 + dy**2)  # Diagonal = 1.414
                tentative_g = g_score[current] + move_cost
                
                if neighbor not in g_score or tentative_g < g_score[neighbor]:
                    came_from[neighbor] = current
                    g_score[neighbor] = tentative_g
                    f_score[neighbor] = tentative_g + self._heuristic(neighbor, goal_grid)
                    heapq.heappush(open_set, (f_score[neighbor], neighbor))
        
        # No path found
        return Path([], 0.0, False, "astar")
    
    def _plan_dijkstra(self, start: Waypoint, goal: Waypoint) -> Path:
        """Dijkstra's algorithm (A* with zero heuristic)"""
        # Similar to A* but without heuristic
        start_grid = self.grid.world_to_grid(start.x, start.y)
        goal_grid = self.grid.world_to_grid(goal.x, goal.y)
        
        if self.grid.is_occupied(*start_grid) or self.grid.is_occupied(*goal_grid):
            return Path([], 0.0, False, "dijkstra")
        
        open_set = []
        heapq.heappush(open_set, (0, start_grid))
        
        came_from = {}
        cost = {start_grid: 0}
        
        while open_set:
            current_cost, current = heapq.heappop(open_set)
            
            if current == goal_grid:
                return self._reconstruct_path(came_from, current, start_grid)
            
            for dx, dy in [(-1,-1), (-1,0), (-1,1), (0,-1), (0,1), (1,-1), (1,0), (1,1)]:
                neighbor = (current[0] + dx, current[1] + dy)
                
                if not self.grid.is_valid_cell(*neighbor):
                    continue
                
                if self.grid.is_occupied(*neighbor):
                    continue
                
                move_cost = math.sqrt(dx**2 + dy**2)
                new_cost = cost[current] + move_cost
                
                if neighbor not in cost or new_cost < cost[neighbor]:
                    cost[neighbor] = new_cost
                    came_from[neighbor] = current
                    heapq.heappush(open_set, (new_cost, neighbor))
        
        return Path([], 0.0, False, "dijkstra")
    
    def _plan_rrt(self, start: Waypoint, goal: Waypoint, 
                 max_iterations: int = 1000) -> Path:
        """Rapidly-exploring Random Tree path planning"""
        # Simplified RRT implementation
        start_grid = self.grid.world_to_grid(start.x, start.y)
        goal_grid = self.grid.world_to_grid(goal.x, goal.y)
        
        if self.grid.is_occupied(*start_grid) or self.grid.is_occupied(*goal_grid):
            return Path([], 0.0, False, "rrt")
        
        # Tree nodes
        tree = {start_grid: None}
        
        goal_threshold = 5  # Grid cells
        step_size = 10  # Grid cells
        
        for _ in range(max_iterations):
            # Sample random point (bias toward goal 10% of time)
            if np.random.random() < 0.1:
                sample = goal_grid
            else:
                sample = (
                    np.random.randint(0, self.grid.grid_width),
                    np.random.randint(0, self.grid.grid_height)
                )
            
            # Find nearest node in tree
            nearest = min(tree.keys(), 
                         key=lambda n: math.sqrt((n[0]-sample[0])**2 + (n[1]-sample[1])**2))
            
            # Step toward sample
            dx = sample[0] - nearest[0]
            dy = sample[1] - nearest[1]
            dist = math.sqrt(dx**2 + dy**2)
            
            if dist == 0:
                continue
            
            # Normalize and scale
            dx = int(dx / dist * step_size)
            dy = int(dy / dist * step_size)
            
            new_node = (nearest[0] + dx, nearest[1] + dy)
            
            # Check if valid
            if not self.grid.is_valid_cell(*new_node):
                continue
            
            if self.grid.is_occupied(*new_node):
                continue
            
            # Add to tree
            tree[new_node] = nearest
            
            # Check if reached goal
            dist_to_goal = math.sqrt(
                (new_node[0] - goal_grid[0])**2 + 
                (new_node[1] - goal_grid[1])**2
            )
            
            if dist_to_goal < goal_threshold:
                # Connect to goal
                tree[goal_grid] = new_node
                return self._reconstruct_path(tree, goal_grid, start_grid)
        
        return Path([], 0.0, False, "rrt")
    
    def _heuristic(self, a: Tuple[int, int], b: Tuple[int, int]) -> float:
        """Heuristic function for A* (Euclidean distance)"""
        return math.sqrt((a[0] - b[0])**2 + (a[1] - b[1])**2)
    
    def _reconstruct_path(self, came_from: Dict, current: Tuple[int, int], 
                         start: Tuple[int, int]) -> Path:
        """Reconstruct path from came_from dictionary"""
        path_grid = [current]
        
        while current in came_from and came_from[current] is not None:
            current = came_from[current]
            path_grid.append(current)
        
        path_grid.reverse()
        
        # Convert to waypoints
        waypoints = []
        total_distance = 0.0
        
        for i, (gx, gy) in enumerate(path_grid):
            x, y = self.grid.grid_to_world(gx, gy)
            wp = Waypoint(x, y)
            waypoints.append(wp)
            
            if i > 0:
                total_distance += waypoints[i].distance_to(waypoints[i-1])
        
        # Simplify path (remove redundant waypoints)
        waypoints = self._simplify_path(waypoints)
        
        return Path(waypoints, total_distance, True, self.planner_type.value)
    
    def _simplify_path(self, waypoints: List[Waypoint]) -> List[Waypoint]:
        """Simplify path by removing collinear points"""
        if len(waypoints) <= 2:
            return waypoints
        
        simplified = [waypoints[0]]
        
        for i in range(1, len(waypoints) - 1):
            # Check if point is collinear with previous and next
            prev = simplified[-1]
            current = waypoints[i]
            next_wp = waypoints[i + 1]
            
            # Calculate cross product
            v1x = current.x - prev.x
            v1y = current.y - prev.y
            v2x = next_wp.x - current.x
            v2y = next_wp.y - current.y
            
            cross = abs(v1x * v2y - v1y * v2x)
            
            # If not collinear (cross product > threshold), keep point
            if cross > 0.01:
                simplified.append(current)
        
        simplified.append(waypoints[-1])
        
        return simplified


if __name__ == "__main__":
    """Test path planner"""
    print("Testing Path Planner Module")
    
    # Create occupancy grid
    grid = OccupancyGrid(width=10.0, height=10.0, resolution=0.1)
    
    # Add some obstacles
    for i in range(30, 70):
        grid.set_occupied(i, 50, occupied=True)
    
    for i in range(30, 70):
        grid.set_occupied(50, i, occupied=True)
    
    # Inflate obstacles
    grid.inflate_obstacles(robot_radius=0.3)
    
    # Create planner
    planner = PathPlanner(PlannerType.ASTAR, grid)
    
    # Plan path
    start = Waypoint(1.0, 1.0)
    goal = Waypoint(8.0, 8.0)
    
    print(f"\nPlanning path from ({start.x}, {start.y}) to ({goal.x}, {goal.y})")
    
    path = planner.plan(start, goal)
    
    if path.is_valid:
        print(f"✓ Path found with {len(path.waypoints)} waypoints")
        print(f"  Total distance: {path.total_distance:.2f}m")
        print(f"  Planner: {path.planner_used}")
        print("\nWaypoints:")
        for i, wp in enumerate(path.waypoints):
            print(f"  {i+1}. ({wp.x:.2f}, {wp.y:.2f})")
    else:
        print("✗ No path found")
    
    # Visualize
    try:
        import cv2
        vis = grid.get_visualization()
        
        # Draw path
        if path.is_valid:
            for i in range(len(path.waypoints) - 1):
                wp1 = path.waypoints[i]
                wp2 = path.waypoints[i + 1]
                
                gx1, gy1 = grid.world_to_grid(wp1.x, wp1.y)
                gx2, gy2 = grid.world_to_grid(wp2.x, wp2.y)
                
                cv2.line(vis, (gx1, gy1), (gx2, gy2), (0, 255, 0), 2)
        
        # Scale up for visibility
        vis = cv2.resize(vis, (500, 500), interpolation=cv2.INTER_NEAREST)
        cv2.imshow("Path Planning", vis)
        print("\nPress any key to close visualization...")
        cv2.waitKey(0)
        cv2.destroyAllWindows()
    except ImportError:
        print("OpenCV not available for visualization")
    
    print("\nTest completed")

