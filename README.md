
🧠 Vision System – Test Overview

This folder contains all test scripts used to validate the Vision Module developed for the Capstone Robotics Project.

📂 modules/

Contains the main computer vision logic.

vision.py →
Implements the VisionSystem class which handles:

RGB frame capture

Depth measurement (center distance)

YOLO object detection with simulated data if no hardware available

📂 test/

Contains modular test scripts for different parts of the vision system.

🧩 test_camera.py

Tests the RGB camera pipeline.
✅ Verifies if frames are being captured successfully.
🧠 Useful for checking that the camera initialization or simulation mode works.

🌊 test_depth.py

Tests the depth sensing function.
✅ Fetches and prints the distance at the center of the frame.
🧠 Helps confirm that the system can measure or simulate depth.

🔄 test_integration.py

Runs a full test of the vision system.
✅ Combines RGB capture, depth sensing, and YOLO detections in a single run.
🧠 Confirms that all components interact properly.

🎯 test_yolo.py

Tests the YOLO-based object detection system.
✅ Simulates detections (in simulation mode).
✅ Displays labels, confidence scores, and 3D spatial coordinates (X, Y, Z).
🧠 Useful for verifying detection logic before connecting real OAK-D hardware.

⚙️ requirements.txt

Lists all dependencies required to run the Vision System:

depthai
opencv-python
numpy

💡 How to Run the Tests

Activate your virtual environment first:

source depthai-env/bin/activate


Then, run each test individually:

python3 -m test.test_camera
python3 -m test.test_depth
python3 -m test.test_yolo
python3 -m test.test_integration

🧪 Output Example
[TEST] RGB frame captured successfully!
[TEST] Center depth: 1.72 meters
[YOLO] person (88.0%) at X=-15mm, Y=42mm, Z=1830mm
Frame captured: True
Center depth: 1.68 meters
Detections: 2 found
=======
# Custom AI Rover Platform

This is the official repository for our Capstone Design project to build an AI-powered autonomous rover using a Jetson Orin NX and 4WD UGV chassis. Our goal is to create an intelligent mobile platform that can navigate autonomously, follow people, respond to voice commands, and provide AI-powered interaction capabilities.

## Project Overview

The Custom AI Rover Platform is designed as a versatile autonomous vehicle that combines:
- **Computer Vision**: Person detection and obstacle avoidance using OAK-D camera
- **Natural Language Processing**: Voice recognition and AI-powered responses
- **Autonomous Movement**: 4WD UGV chassis with independent wheel control for superior maneuverability
- **Real-time Processing**: All running on NVIDIA Jetson Orin NX for edge AI computing

## Hardware Components
- NVIDIA Jetson Orin NX (main computing unit)
- OAK-D Camera (depth perception and computer vision)
- 4WD UGV Chassis with independent motor control
- Speakers and microphone for audio interaction
- Various sensors for environmental awareness

## Team Members
- **Dilmurod**: Motor Control & Hardware Integration
- **Sabera**: Computer Vision & Object Detection  
- **Boymirzo**: Audio Processing & AI Integration

---

## Module API Contract
This document defines the official functions our software modules will use to communicate with `main.py`.

### `modules/motor_control.py` (Owner: Dilmurod)
*This module handles all physical movement for the 4WD UGV chassis.*

- **`setup() -> None:`**
  - Initializes all GPIO pins for 4WD motor control.
  - Must be called before any other motor functions.
  - Raises `RuntimeError` if GPIO initialization fails.

- **`move(front_left: int, front_right: int, rear_left: int, rear_right: int) -> None:`**
  - Sets the speed of each wheel independently for maximum maneuverability.
  - Speed is an integer from -100 (full reverse) to 100 (full forward).
  - `front_left`: Speed for front left wheel (-100 to 100)
  - `front_right`: Speed for front right wheel (-100 to 100)
  - `rear_left`: Speed for rear left wheel (-100 to 100)
  - `rear_right`: Speed for rear right wheel (-100 to 100)
  - Raises `ValueError` if speeds are outside valid range.

- **`move_simple(forward_speed: int, turn_speed: int) -> None:`**
  - Simplified movement control for basic forward/backward and turning.
  - `forward_speed`: Forward/backward speed (-100 to 100)
  - `turn_speed`: Turning speed (-100 left to 100 right)
  - Automatically calculates individual wheel speeds.

- **`stop() -> None:`**
  - Immediately stops all motors.
  - Safe to call multiple times.

- **`cleanup() -> None:`**
  - Releases all GPIO pins safely when the program exits.
  - Should be called in exception handlers and at program termination.

---

### `modules/vision.py` (Owner: Sabera)
*This module handles all input from the OAK-D camera.*

- **`setup() -> None:`**
  - Initializes the OAK-D camera and computer vision pipeline.
  - Must be called before any other vision functions.
  - Raises `RuntimeError` if camera initialization fails.

- **`get_latest_frame() -> numpy.ndarray:`**
  - Returns the latest color image frame as a NumPy array.
  - Format: BGR color image (OpenCV standard)
  - Shape: (height, width, 3)
  - Returns `None` if no frame is available.

- **`is_person_detected() -> bool:`**
  - Returns `True` if a person is detected in the current frame, otherwise `False`.
  - Uses YOLO or similar object detection model.
  - Updates automatically with each new frame.

- **`get_obstacle_distance() -> float:`**
  - Returns the distance in meters to the nearest obstacle directly in front of the robot.
  - Uses depth information from OAK-D camera.
  - Returns `float('inf')` if no obstacle is detected within range.
  - Range: 0.5 to 10.0 meters (camera limitations).

- **`cleanup() -> None:`**
  - Properly closes camera connections and releases resources.

---

### `modules/audio.py` (Owner: Boymirzo)
*This module handles all audio input and output.*

- **`setup() -> None:`**
  - Initializes audio hardware (microphone and speakers).
  - Sets up speech recognition and text-to-speech engines.
  - Must be called before any other audio functions.
  - Raises `RuntimeError` if audio hardware initialization fails.

- **`listen_and_transcribe() -> str:`**
  - Listens for speech, transcribes it, and returns the recognized text as a string.
  - Blocks until speech is detected and processed.
  - Returns empty string `""` if no speech is recognized.
  - Timeout: 5 seconds of silence before returning.

- **`speak(text: str) -> None:`**
  - Takes a string of text and speaks it out loud using text-to-speech.
  - `text`: The message to be spoken
  - Non-blocking: returns immediately while speech continues in background.
  - Raises `ValueError` if text is empty or None.

- **`get_intelligent_response(prompt: str) -> str:`**
  - Sends a text prompt to the LLM and returns the AI's response.
  - `prompt`: User's question or statement to send to AI
  - Returns the AI's response as a string.
  - Handles API rate limiting and network errors gracefully.
  - Returns error message if LLM is unavailable.

- **`cleanup() -> None:`**
  - Stops any ongoing speech and releases audio resources.

---

## Main Program Structure

The `main.py` file will orchestrate all modules:

```python
# Example usage of the API contract
import modules.motor_control as motor
import modules.vision as vision  
import modules.audio as audio

def main():
    # Initialize all modules
    motor.setup()
    vision.setup()
    audio.setup()
    
    try:
        while True:
            # Check for person and follow
            if vision.is_person_detected():
                # Simple following logic using simplified movement
                motor.move_simple(50, 0)  # Move forward
            else:
                motor.stop()
            
            # Check for obstacles
            distance = vision.get_obstacle_distance()
            if distance < 1.0:  # Too close to obstacle
                motor.stop()
                # Turn right to avoid obstacle
                motor.move_simple(0, 30)
            
            # Listen for voice commands
            command = audio.listen_and_transcribe()
            if command:
                response = audio.get_intelligent_response(command)
                audio.speak(response)
                
    except KeyboardInterrupt:
        print("Shutting down...")
    finally:
        # Clean up all modules
        motor.cleanup()
        vision.cleanup()
        audio.cleanup()

if __name__ == "__main__":
    main()
```

## Development Guidelines

1. **Error Handling**: All modules must handle errors gracefully and provide meaningful error messages.
2. **Documentation**: Each function should include docstrings with parameter descriptions and return values.
3. **Testing**: Create unit tests for each module's functions.
4. **Dependencies**: Document all required Python packages in `requirements.txt`.
5. **Hardware Safety**: Motor control must include emergency stop functionality.

## Getting Started

1. Clone this repository
2. Install dependencies: `pip install -r requirements.txt`
3. Connect hardware components according to wiring diagram
4. Run the main program: `python main.py`

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
>>>>>>> dea377af4274e5124b4eca662e9282d676801953
