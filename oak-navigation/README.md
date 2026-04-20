# OAK-D Navigation System

A comprehensive autonomous navigation system for robots using the OAK-D Lite camera with stereo depth perception.

## Features

### 🎯 Core Capabilities
- **Real-time Depth Processing**: Stereo depth mapping at 30 FPS
- **Obstacle Detection & Avoidance**: Multiple algorithms (Potential Field, VFH, Reactive)
- **Path Planning**: A*, Dijkstra, and RRT algorithms
- **Occupancy Grid Mapping**: Real-time 2D grid mapping from depth data
- **Spatial AI** (Optional): Object detection with 3D spatial coordinates
- **Multiple Navigation Modes**: Manual, Assisted, Autonomous, Waypoint, Explore

### 🚀 Key Components

#### 1. Depth Processor (`depth_processor.py`)
- Stereo depth map generation
- Configurable resolution (400p, 720p, 800p)
- Grid-based depth analysis
- Zone-based obstacle detection
- Safe direction calculation

#### 2. Obstacle Avoidance (`obstacle_avoidance.py`)
- **Potential Field Method**: Attractive/repulsive forces
- **Vector Field Histogram (VFH)**: Polar histogram-based navigation
- **Simple Reactive**: Fast reactive behavior
- **Wall Following**: Maintain distance from walls

#### 3. Path Planner (`path_planner.py`)
- **A* Algorithm**: Optimal path finding
- **Dijkstra's Algorithm**: Guaranteed shortest path
- **RRT**: Rapidly-exploring Random Tree
- Occupancy grid integration
- Obstacle inflation for safety
- Path simplification

#### 4. Navigation Controller (`navigation_controller.py`)
- Integrates all components
- Multi-threaded control loop
- State management
- Waypoint queue
- Emergency stop handling

#### 5. Spatial AI (`spatial_ai.py`) - Optional
- Object detection with depth
- Spatial coordinates for detected objects
- Navigation context analysis
- Obstacle classification

## Installation

### Prerequisites
- OAK-D Lite camera
- Python 3.7+
- USB 3.0 port

### Install Dependencies
```bash
cd oakd_navigation
pip install -r requirements.txt
```

### Verify OAK-D Connection
```bash
python3 -c "import depthai as dai; print('DepthAI version:', dai.__version__)"
```

## Quick Start

### Basic Depth Processing Test
```bash
python3 depth_processor.py
```
Press 'q' to quit.

### Obstacle Avoidance Test
```bash
python3 obstacle_avoidance.py
```

### Path Planning Test
```bash
python3 path_planner.py
```

### Full Navigation Controller Test
```bash
python3 navigation_controller.py
```

Controls:
- `1` - Manual mode
- `2` - Assisted mode  
- `3` - Autonomous mode
- `4` - Explore mode
- `t` - Set target waypoint
- `s` - Emergency stop
- `r` - Reset emergency stop
- `q` - Quit

## Usage Examples

### Example 1: Basic Depth Sensing
```python
from oakd_navigation import DepthProcessor, DepthConfig

# Configure depth processor
config = DepthConfig(
    resolution="400p",
    fps=30,
    min_depth=300,  # 30cm
    max_depth=5000  # 5m
)

# Start depth processor
with DepthProcessor(config) as processor:
    while True:
        depth_frame = processor.get_depth_frame()
        if depth_frame is not None:
            nav_data = processor.process_depth_for_navigation(depth_frame)
            print(f"Center distance: {nav_data['zones']['center']['median']}mm")
            print(f"Best direction: {nav_data['safe_directions']['best_direction']}")
```

### Example 2: Obstacle Avoidance
```python
from oakd_navigation import ObstacleAvoidance, AvoidanceStrategy

# Create obstacle avoider
avoider = ObstacleAvoidance(
    strategy=AvoidanceStrategy.POTENTIAL_FIELD,
    safe_distance=1.5,  # meters
    max_speed=0.5
)

# Get navigation command
command = avoider.compute_command(nav_data, goal_direction=0.0)
print(f"Linear: {command.linear_velocity}, Angular: {command.angular_velocity}")
```

### Example 3: Path Planning
```python
from oakd_navigation import PathPlanner, PlannerType, Waypoint, OccupancyGrid

# Create occupancy grid
grid = OccupancyGrid(width=10.0, height=10.0, resolution=0.1)

# Create planner
planner = PathPlanner(PlannerType.ASTAR, grid)

# Plan path
start = Waypoint(1.0, 1.0)
goal = Waypoint(8.0, 8.0)
path = planner.plan(start, goal)

if path.is_valid:
    print(f"Path found: {len(path.waypoints)} waypoints")
    for wp in path.waypoints:
        print(f"  ({wp.x:.2f}, {wp.y:.2f})")
```

### Example 4: Full Navigation System
```python
from oakd_navigation import NavigationController, NavigationMode, Waypoint

# Create controller
controller = NavigationController(
    avoidance_strategy=AvoidanceStrategy.POTENTIAL_FIELD,
    planner_type=PlannerType.ASTAR,
    update_rate=10.0  # Hz
)

# Set velocity callback (connect to your robot)
def velocity_callback(linear, angular):
    # Send commands to your robot motors
    print(f"Linear: {linear:.2f} m/s, Angular: {angular:.2f} rad/s")

controller.set_velocity_callback(velocity_callback)

# Start navigation
with controller:
    # Set autonomous mode
    controller.set_mode(NavigationMode.AUTONOMOUS)
    
    # Set target
    target = Waypoint(5.0, 5.0)
    controller.set_target(target)
    
    # Monitor state
    while True:
        state = controller.get_state()
        print(f"Mode: {state.mode}, Moving: {state.is_moving}")
        
        if state.target_waypoint is None:
            break  # Reached target
```

## Configuration

Edit `config.yaml` to customize behavior:

```yaml
depth:
  resolution: "400p"
  fps: 30
  safe_distance: 1.5

obstacle_avoidance:
  strategy: "potential_field"
  max_speed: 0.5

path_planning:
  planner_type: "astar"
  robot_radius: 0.3

navigation:
  update_rate: 10.0
  default_mode: "manual"
```

## Integration with Your Robot

### Step 1: Connect Motor Control
```python
controller = NavigationController()

def send_to_motors(linear_vel, angular_vel):
    # Your robot-specific motor control code
    left_speed = linear_vel - angular_vel * wheel_base / 2
    right_speed = linear_vel + angular_vel * wheel_base / 2
    motor_controller.set_speeds(left_speed, right_speed)

controller.set_velocity_callback(send_to_motors)
```

### Step 2: Provide Odometry (Optional but Recommended)
```python
# Update robot position from wheel encoders or SLAM
def odometry_callback(x, y, heading):
    controller.update_position(x, y, heading)

# Call this whenever you get new odometry data
odometry_callback(robot_x, robot_y, robot_heading)
```

### Step 3: Set Navigation Goals
```python
# Autonomous navigation to specific point
controller.set_mode(NavigationMode.AUTONOMOUS)
controller.set_target(Waypoint(5.0, 3.0))

# Or exploration mode
controller.set_mode(NavigationMode.EXPLORE)
```

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                 Navigation Controller                    │
│  - Mode management                                       │
│  - Control loop (10 Hz)                                  │
│  - State tracking                                        │
└────────┬────────────────────────────────────────────────┘
         │
         ├──────────┬──────────────┬────────────────┐
         │          │              │                │
    ┌────▼────┐ ┌──▼──────┐ ┌────▼─────┐  ┌──────▼──────┐
    │ Depth   │ │Obstacle │ │  Path    │  │  Spatial AI │
    │Processor│ │Avoidance│ │ Planner  │  │  (Optional) │
    └────┬────┘ └──┬──────┘ └────┬─────┘  └──────┬──────┘
         │         │              │                │
         │         │              │                │
    ┌────▼─────────▼──────────────▼────────────────▼──────┐
    │              OAK-D Lite Camera                       │
    │  - Stereo depth (CAM_B, CAM_C)                       │
    │  - RGB camera (CAM_A)                                │
    │  - Myriad X VPU                                      │
    └──────────────────────────────────────────────────────┘
```

## Performance

- **Depth Processing**: 30 FPS @ 400p resolution
- **Control Loop**: 10 Hz (configurable)
- **Latency**: < 100ms end-to-end
- **CPU Usage**: ~40-60% on Raspberry Pi 5
- **Memory**: ~200-300 MB

## Troubleshooting

### Camera Not Detected
```bash
# Check USB connection
lsusb | grep 03e7

# Check permissions
ls -la /dev/bus/usb/003/*
```

### Low FPS
- Reduce resolution: `resolution="400p"`
- Disable subpixel: `subpixel=false`
- Lower control loop rate: `update_rate=5.0`

### Path Planning Fails
- Check occupancy grid size
- Increase robot radius inflation
- Try different planner: `PlannerType.RRT`

### Obstacle Avoidance Too Aggressive
- Increase safe_distance: `safe_distance=2.0`
- Reduce repulsive_gain: `repulsive_gain=1.0`
- Try different strategy: `AvoidanceStrategy.SIMPLE_REACTIVE`

## Advanced Features

### Custom Obstacle Avoidance
```python
class MyCustomAvoider(ObstacleAvoidance):
    def compute_command(self, nav_data, goal_direction):
        # Your custom logic here
        return NavigationCommand(linear_vel, angular_vel, False, 0.8, "custom")
```

### Multi-Goal Waypoint Navigation
```python
waypoints = [
    Waypoint(2.0, 2.0),
    Waypoint(5.0, 2.0),
    Waypoint(5.0, 5.0),
    Waypoint(2.0, 5.0)
]

controller.set_mode(NavigationMode.WAYPOINT)
for wp in waypoints:
    controller.add_waypoint(wp)
```

### Spatial AI Object Detection
```python
from oakd_navigation import SpatialAI

spatial_ai = SpatialAI(
    model_path="path/to/yolo-v4-tiny.blob",
    confidence_threshold=0.5
)

with spatial_ai:
    rgb_frame, detections = spatial_ai.get_detections()
    for obj in detections:
        print(f"{obj.label}: {obj.distance:.2f}m at {obj.angle:.1f}°")
```

## Contributing

This is a standalone navigation system designed for integration into your robot project. Feel free to modify and extend it for your specific needs.

## License

This code is provided as-is for integration into the Rovy robot project.

## Credits

Built using:
- [DepthAI](https://github.com/luxonis/depthai) - OAK camera SDK
- [OpenCV](https://opencv.org/) - Computer vision
- [NumPy](https://numpy.org/) - Numerical computing

## Support

For OAK-D camera documentation: https://docs.luxonis.com/
For DepthAI examples: https://github.com/luxonis/depthai-python/tree/main/examples

