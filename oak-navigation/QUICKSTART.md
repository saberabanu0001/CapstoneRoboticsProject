# OAK-D Navigation - Quick Start Guide

## 🚀 Get Started in 5 Minutes

### Step 1: Verify Installation
```bash
cd /home/rovy/rovy_client/oakd_navigation
python3 test_system.py
```

This will test:
- ✓ All dependencies installed
- ✓ OAK-D camera detected
- ✓ Depth processing working
- ✓ All navigation modules functional

### Step 2: Test Depth Sensing
```bash
python3 depth_processor.py
```

You should see:
- Real-time depth visualization
- Distance measurements (Left, Center, Right)
- Best navigation direction
- FPS counter

**Press 'q' to quit**

### Step 3: Run Navigation Controller
```bash
python3 navigation_controller.py
```

**Controls:**
- `1` = Manual mode (no autonomous control)
- `2` = Assisted mode (obstacle avoidance only)
- `3` = Autonomous mode (navigate to target)
- `4` = Explore mode (autonomous exploration)
- `t` = Set target 5m ahead
- `s` = Emergency stop
- `r` = Reset emergency stop
- `q` = Quit

### Step 4: Try Examples

#### Simple Exploration
```bash
cd examples
python3 simple_navigation.py
```

Robot will explore autonomously for 30 seconds, avoiding obstacles.

#### Waypoint Navigation
```bash
python3 waypoint_navigation.py
```

Robot will navigate through a square pattern.

## 🔧 Integration with Your Robot

### Minimal Integration Example

```python
from oakd_navigation import NavigationController, NavigationMode

# Create controller
nav = NavigationController()

# Connect to your robot motors
def send_to_motors(linear_vel, angular_vel):
    # YOUR CODE HERE: Send velocities to motors
    print(f"Linear: {linear_vel}, Angular: {angular_vel}")

nav.set_velocity_callback(send_to_motors)

# Start navigation
nav.start()

# Set explore mode
nav.set_mode(NavigationMode.EXPLORE)

# Let it run...
# nav.stop() when done
```

## 📊 What Each Component Does

### 1. **Depth Processor** (`depth_processor.py`)
- Gets stereo depth from OAK-D
- Analyzes obstacles in left/center/right zones
- Calculates safe directions
- Provides grid-based depth map

### 2. **Obstacle Avoidance** (`obstacle_avoidance.py`)
- Takes depth data
- Computes velocity commands (linear, angular)
- Multiple algorithms available:
  - **Potential Field**: Best for open spaces
  - **VFH**: Good for complex environments
  - **Simple Reactive**: Fast, basic avoidance
  - **Wall Following**: Follows walls

### 3. **Path Planner** (`path_planner.py`)
- Plans optimal path from A to B
- Builds occupancy grid from depth data
- Algorithms: A*, Dijkstra, RRT
- Handles obstacle inflation for safety

### 4. **Navigation Controller** (`navigation_controller.py`)
- Integrates everything
- Runs control loop at 10 Hz
- Manages navigation modes
- Handles waypoint queues

## 🎯 Common Use Cases

### Use Case 1: Obstacle Avoidance Only
```python
from oakd_navigation import DepthProcessor, ObstacleAvoidance

processor = DepthProcessor()
avoider = ObstacleAvoidance()

processor.start()

while True:
    depth = processor.get_depth_frame()
    if depth:
        nav_data = processor.process_depth_for_navigation(depth)
        command = avoider.compute_command(nav_data)
        # Send command.linear_velocity and command.angular_velocity to motors
```

### Use Case 2: Navigate to Specific Point
```python
from oakd_navigation import NavigationController, NavigationMode, Waypoint

nav = NavigationController()
nav.set_velocity_callback(your_motor_function)
nav.start()

nav.set_mode(NavigationMode.AUTONOMOUS)
nav.set_target(Waypoint(5.0, 3.0))  # Navigate to (5m, 3m)

# Monitor progress
while nav.get_state().target_waypoint is not None:
    time.sleep(0.5)

print("Reached target!")
```

### Use Case 3: Follow Waypoint Path
```python
nav.set_mode(NavigationMode.WAYPOINT)

waypoints = [
    Waypoint(2, 2),
    Waypoint(5, 2),
    Waypoint(5, 5),
]

for wp in waypoints:
    nav.add_waypoint(wp)

# Will navigate through all waypoints
```

## ⚙️ Configuration

Edit `config.yaml` for your robot:

```yaml
obstacle_avoidance:
  safe_distance: 1.5  # Minimum distance from obstacles (meters)
  max_speed: 0.5      # Maximum speed (m/s)

path_planning:
  robot_radius: 0.3   # Your robot's radius (meters)

navigation:
  update_rate: 10.0   # Control loop frequency (Hz)
```

## 🐛 Troubleshooting

### "No OAK-D devices found"
```bash
# Check USB connection
lsusb | grep 03e7

# Should see: "03e7:f63b Intel Myriad VPU"
```

### "Camera already in use"
```bash
# Stop other processes using camera
pkill -f depthai
pkill -f oak
```

### Robot moves too fast/slow
Edit `config.yaml`:
```yaml
obstacle_avoidance:
  max_speed: 0.3  # Reduce for slower movement
```

### Too sensitive to obstacles
Edit `config.yaml`:
```yaml
obstacle_avoidance:
  safe_distance: 2.0  # Increase for more caution
```

## 📈 Performance Tips

### For Raspberry Pi 4/5:
- Use `resolution: "400p"` (default)
- Keep `update_rate: 10.0` (default)
- Disable spatial AI if not needed

### For More Powerful Hardware:
- Use `resolution: "720p"` for better depth
- Increase `update_rate: 20.0` for faster response
- Enable spatial AI for object detection

## 🎓 Next Steps

1. **Test in safe environment** - Start with open space
2. **Tune parameters** - Adjust speeds and distances for your robot
3. **Add odometry** - Integrate wheel encoders or SLAM for better navigation
4. **Add spatial AI** - Detect and classify objects (requires neural network model)

## 📚 Full Documentation

See `README.md` for complete API documentation and advanced features.

## 🆘 Need Help?

- Check `README.md` for detailed documentation
- Run `python3 test_system.py` to diagnose issues
- Review example scripts in `examples/` directory

