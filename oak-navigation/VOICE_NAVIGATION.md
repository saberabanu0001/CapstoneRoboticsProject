# Voice-Controlled Navigation

This guide explains how to use voice commands to control Rovy's autonomous navigation system.

## Overview

The voice-controlled navigation system integrates three components:
1. **Robot Client** (Raspberry Pi) - Handles wake word detection and executes navigation commands
2. **Cloud Server** (PC) - Processes voice commands using Whisper STT and sends navigation commands
3. **OAK-D Navigation** - Autonomous navigation with obstacle avoidance using the OAK-D camera

## Architecture

```
┌─────────────────────────────┐
│    Raspberry Pi (Robot)     │
│  ┌─────────────────────┐    │
│  │  Wake Word Detector │    │
│  │  (Silero VAD +      │    │
│  │   Whisper Tiny)     │    │
│  └──────────┬──────────┘    │
│             │                │
│             v                │
│  ┌─────────────────────┐    │
│  │  Audio Recording    │    │
│  └──────────┬──────────┘    │
│             │                │
│             v WebSocket      │
└─────────────┼────────────────┘
              │
              v
┌─────────────┴────────────────┐
│    Cloud Server (PC)         │
│  ┌─────────────────────┐     │
│  │  Whisper STT        │     │
│  │  (Speech to Text)   │     │
│  └──────────┬──────────┘     │
│             │                │
│             v                │
│  ┌─────────────────────┐     │
│  │  Command Parser     │     │
│  │  (Detect Navigation │     │
│  │   Keywords)         │     │
│  └──────────┬──────────┘     │
│             │                │
│             v WebSocket      │
└─────────────┼────────────────┘
              │
              v
┌─────────────┴────────────────┐
│    Raspberry Pi (Robot)      │
│  ┌─────────────────────┐     │
│  │  Navigation Handler │     │
│  └──────────┬──────────┘     │
│             │                │
│             v                │
│  ┌─────────────────────┐     │
│  │  RovyNavigator      │     │
│  │  (OAK-D Integration)│     │
│  └──────────┬──────────┘     │
│             │                │
│             v                │
│  ┌─────────────────────┐     │
│  │  NavigationController│    │
│  │  + ObstacleAvoidance│     │
│  └──────────┬──────────┘     │
│             │                │
│             v                │
│  ┌─────────────────────┐     │
│  │  Rover Motors       │     │
│  └─────────────────────┘     │
└──────────────────────────────┘
```

## Voice Commands

### Start Navigation

Say any of these phrases after the wake word:
- **"start auto navigation"**
- **"start autonomous navigation"**
- **"begin auto navigation"**
- **"start explore"**
- **"begin exploration"**

Example:
```
You: "Hey Rovy, start auto navigation"
Rovy: "Starting autonomous navigation. I will explore and avoid obstacles."
[Robot begins autonomous exploration]
```

### Stop Navigation

Say any of these phrases:
- **"stop navigation"**
- **"stop auto navigation"**
- **"end navigation"**
- **"stop exploring"**

Example:
```
You: "Hey Rovy, stop navigation"
Rovy: "Stopping navigation."
[Robot stops and navigation system shuts down]
```

## Setup

### 1. Prerequisites

Ensure you have the following installed and configured:

#### On Raspberry Pi:
- Wake word detector with Silero VAD + Whisper (see `robot/wake_word_detector.py`)
- OAK-D camera connected
- All navigation dependencies (see `oakd_navigation/README.md`)

#### On PC (Cloud Server):
- Whisper model for STT
- Cloud server running (`cloud/main.py`)

### 2. Start the Services

#### On Raspberry Pi:
```bash
cd /home/rovy/rovy_client/robot
python main.py
```

This will:
- Connect to the rover via serial
- Initialize the wake word detector
- Connect to the cloud server via WebSocket
- Start listening for wake words

#### On PC:
```bash
cd /home/rovy/rovy_client/cloud
python main.py
```

This will:
- Start the WebSocket server
- Load the Whisper STT model
- Wait for robot connections

### 3. Test the System

1. Say the wake word: **"Hey Rovy"**
2. Wait for acknowledgment
3. Say: **"start auto navigation"**
4. The robot should respond and begin exploring

## How It Works

### Wake Word Detection

The robot continuously listens for wake words using:
- **Silero VAD (Voice Activity Detection)**: Detects when speech is happening
- **Whisper Tiny**: Transcribes the speech to verify wake word

This runs locally on the Raspberry Pi for low latency.

### Command Processing

1. When wake word is detected, the robot records the following query
2. Audio is sent to the cloud server via WebSocket
3. Cloud server uses Whisper STT to transcribe the audio
4. Command parser checks for navigation keywords:
   - `start` + `auto`/`autonomous` + `navigation`
   - `start`/`begin` + `explore`
   - `stop` + `navigation`

### Navigation Execution

When a start command is detected:

1. Cloud server sends navigation message:
   ```json
   {
     "type": "navigation",
     "action": "start_explore",
     "duration": null
   }
   ```

2. Robot client receives the message and:
   - Creates a `RovyNavigator` instance (if not already created)
   - Passes the existing Rover instance to avoid serial port conflicts
   - Starts the navigation system
   - Enters exploration mode

3. The `RovyNavigator`:
   - Initializes the OAK-D camera for depth sensing
   - Starts the `NavigationController`
   - Configures obstacle avoidance with Potential Field method
   - Begins autonomous exploration

4. Robot explores autonomously:
   - Moves forward when path is clear
   - Avoids obstacles detected by OAK-D
   - Turns to explore new directions when blocked
   - Updates OLED display with status

## Code Structure

### Modified Files

#### `robot/main.py`
- Added `handle_navigation()` method to process navigation commands
- Dynamically loads `RovyNavigator` when needed
- Runs navigation in separate thread to avoid blocking WebSocket

#### `cloud/main.py`
- Added navigation keyword detection in `process_query()`
- Added `send_navigation()` method to send navigation commands to robot
- Detects commands like "start auto navigation" and "stop navigation"

#### `oakd_navigation/rovy_integration.py`
- Modified `__init__()` to accept existing `rover_instance` parameter
- Prevents serial port conflicts by reusing existing Rover connection
- Added `_owns_rover` flag to manage cleanup properly

## Configuration

### Wake Words

Configure in `robot/config.py`:
```python
WAKE_WORDS = ["hey rovy", "rovy", "hey robot", "hey"]
```

### Navigation Parameters

Configure in `oakd_navigation/rovy_integration.py`:
```python
# Safe distance for obstacle avoidance
safe_distance=0.6  # 60cm

# Speed settings
max_speed=0.4      # Moderate speed
min_speed=0.15     # Minimum speed

# Depth sensing
min_depth=400      # 40cm - ignore ground
max_depth=5000     # 5m - indoor use
```

## Troubleshooting

### Wake Word Not Detected

- Check microphone is working: `arecord -l`
- Verify ReSpeaker is detected in audio devices
- Lower VAD threshold in `robot/config.py`:
  ```python
  VAD_THRESHOLD = 0.15  # Try even lower like 0.10
  ```
- Check wake word detector logs for detection attempts

### Robot Doesn't Start Navigation

- Verify WebSocket connection between robot and server
- Check robot logs for errors when importing navigation modules
- Ensure OAK-D camera is connected
- Try running navigation directly: `python oakd_navigation/rovy_integration.py`

### Robot Stops Immediately

- Check OAK-D depth sensing is working: `python oakd_navigation/debug_depth.py`
- Verify minimum depth is set correctly (not detecting ground)
- Check for obstacles in front of robot
- Review navigation logs for emergency stops

### Voice Command Not Recognized

- Check cloud server logs for transcription output
- Verify Whisper STT is working
- Try more specific commands: "start auto navigation" instead of "go"
- Check for network latency between robot and server

## Advanced Usage

### Custom Duration

Modify `cloud/main.py` to support duration commands:
```python
# Extract duration from query
import re
duration_match = re.search(r'(\d+)\s*(second|minute|min)', query_lower)
if duration_match:
    duration = int(duration_match.group(1))
    if 'minute' in duration_match.group(2):
        duration *= 60
    await self.send_navigation(websocket, action='start_explore', duration=duration)
```

### Waypoint Navigation

Add waypoint commands:
```python
# In cloud/main.py
if 'go to' in query_lower or 'navigate to' in query_lower:
    # Parse coordinates
    coords = re.findall(r'(-?\d+\.?\d*)', query_lower)
    if len(coords) >= 2:
        x, y = float(coords[0]), float(coords[1])
        await self.send_navigation(websocket, action='goto', x=x, y=y)
        await self.send_speak(websocket, f"Navigating to position {x}, {y}")
```

### Integration with Other Services

The navigation system can be integrated with other services:
- Map building and localization
- Object detection and tracking
- Multi-robot coordination
- Path recording and replay

## Safety Features

The system includes multiple safety features:

1. **Obstacle Avoidance**: OAK-D depth sensing detects obstacles 40cm-5m away
2. **Emergency Stop**: `_stop_callback()` immediately stops motors on critical obstacles
3. **Safe Distance**: 60cm buffer maintained from obstacles
4. **Speed Limits**: Max speed 0.4 m/s for safe indoor operation
5. **Potential Field Method**: Naturally avoids obstacles with smooth trajectories
6. **Timeout Support**: Can limit exploration duration
7. **Ctrl+C Handling**: Clean shutdown on keyboard interrupt

## Future Enhancements

Potential improvements:
- [ ] Add visual navigation feedback on OLED
- [ ] Support custom waypoint lists via voice
- [ ] Add "follow me" mode using person detection
- [ ] Implement SLAM for map building
- [ ] Add path recording and replay
- [ ] Multi-language wake word support
- [ ] Gesture control integration
- [ ] Remote monitoring via web interface

## Resources

- Main navigation documentation: `oakd_navigation/README.md`
- Integration guide: `oakd_navigation/INTEGRATION_SUMMARY.md`
- Quick start: `oakd_navigation/QUICKSTART.md`
- Wake word detector: `robot/wake_word_detector.py`
- Cloud server: `cloud/main.py`
- Robot client: `robot/main.py`

## Support

If you encounter issues:
1. Check all service logs
2. Verify hardware connections (OAK-D, serial, microphone)
3. Test components individually
4. Review configuration files
5. Check network connectivity between robot and server

