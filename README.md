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