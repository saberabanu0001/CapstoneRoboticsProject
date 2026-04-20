"""
OAK-D Navigation System
Autonomous navigation using OAK-D Lite camera with depth perception
"""

from .depth_processor import DepthProcessor, DepthConfig
from .obstacle_avoidance import ObstacleAvoidance, AvoidanceStrategy, NavigationCommand
from .path_planner import PathPlanner, PlannerType, Waypoint, Path, OccupancyGrid
from .navigation_controller import NavigationController, NavigationMode, NavigationState

try:
    from .spatial_ai import SpatialAI, SpatialObject
    SPATIAL_AI_AVAILABLE = True
except ImportError:
    SPATIAL_AI_AVAILABLE = False

__version__ = "1.0.0"
__all__ = [
    # Core components
    "NavigationController",
    "DepthProcessor",
    "ObstacleAvoidance",
    "PathPlanner",
    
    # Configuration
    "DepthConfig",
    "NavigationMode",
    "NavigationState",
    "AvoidanceStrategy",
    "PlannerType",
    
    # Data structures
    "Waypoint",
    "Path",
    "NavigationCommand",
    "OccupancyGrid",
    
    # Optional AI
    "SpatialAI",
    "SpatialObject",
    "SPATIAL_AI_AVAILABLE",
]

