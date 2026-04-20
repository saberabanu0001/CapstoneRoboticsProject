# Autonomous UGV - Jetson Orin

🏆 **Award-Winning Capstone Design Project | Best Innovation Award**

<table align="center">
  <tr>
    <td align="center" valign="top" width="50%">
      <img src="image/group_award%20time.jpeg" width="300" alt="Capstone team with Best Innovation Award" />
    </td>
    <td align="center" valign="top" width="50%">
      <img src="image/me%20with%20professors%20with%20award.jpeg" width="300" alt="With faculty and the Best Innovation Award" />
      <br /><br />
      <img src="image/robot_image.jpg" width="300" alt="Autonomous UGV prototype with OAK-D stereo camera and Jetson Orin" />
    </td>
  </tr>
</table>

<p align="center"><em><b>Best Innovation Award</b> — capstone showcase and recognition with the project team and advisors.</em></p>
<p align="center"><em>The physical <b>UGV</b> prototype: <b>OAK-D</b> stereo depth, sensing stack, and <b>NVIDIA Jetson Orin</b> edge compute.</em></p>

A capstone **UGV** stack built around **NVIDIA Jetson-class** edge hardware, **Luxonis OAK-D** stereo depth, and Python/TypeScript components you can run and extend in this repo. It emphasizes **computer vision**, **depth-driven navigation**, and a **mobile operator experience**—not every subsystem (e.g. full SLAM or fleet cloud) ships as production infrastructure here.

## ⚡ Key Highlights

- **🏆 Best Innovation Award** — Recognized for outstanding technical innovation
- **⚡ Real-time perception** — DepthAI pipelines with YOLO-style detection on OAK-D; PyTorch for auxiliary models (e.g. wake word / VLM experiments)
- **🎯 Integrated stack** — Shared `modules/` vision code, `oak-navigation/` depth and planning, `robot/` on-device services, and an Expo **mobile** operator app
- **🔬 Edge-first AI** — Stereo depth, obstacle reasoning, and neural blobs tuned for Jetson-class edge hardware
- **📊 Capstone-grade integration** — End-to-end demos from camera to actuation, with repeatable tests under `test/`
- **🌐 Connected operator UX** — Mobile app with BLE, HTTP, and optional WebSocket-style telemetry to the robot
- **🚀 Modular layout** — Clear separation of perception, navigation, control, and mobile code paths for extension

## 🎯 Project Overview

This award-winning capstone project delivers an **edge-first** autonomous robotics stack: stereo vision and detection in `modules/`, depth-based navigation and planning in `oak-navigation/`, on-robot services in `robot/`, and a cross-platform **Expo** mobile app. The focus is real-time perception, local decision-making, and control, with optional cloud-backed APIs (e.g. speech) where configured—not a separate microservices repo shipped here.

**Key Achievement**: Recognized with the **Best Innovation Award** for outstanding technical innovation and practical implementation in autonomous systems.

## 🚀 Core Features & Technical Achievements

### AI & Machine Learning
- **Deep learning perception**: YOLO-style object detection via DepthAI neural blobs (COCO); optional PyTorch workflows for VAD/VLM experiments in the repo
- **Computer vision pipeline**: OAK-D stereo depth, RGB preview, and OpenCV-based processing (`modules/vision.py` and related tests)
- **Navigation stack**: Grid-based planning and obstacle reasoning in `oak-navigation/` (not RL-trained agents in this codebase)
- **Model delivery**: DepthAI `.blob` models and documented paths under `models/` (see repository note below)

### Autonomous Navigation
- **Depth-centric navigation**: Occupancy-style reasoning, obstacle avoidance (e.g. potential field, VFH, reactive modes in `oak-navigation/`), and integration notes for external odometry or SLAM
- **Obstacle avoidance**: Primarily **stereo depth** from OAK-D; additional sensors (e.g. LiDAR) appear in product/UI wiring as extension points rather than a fully fused driver stack in this repo alone
- **Path planning**: A-star, Dijkstra, and RRT planners over occupancy grids (`oak-navigation/object_detection/path_planner.py`)
- **State updates**: Waypoints and pose updates designed to consume **external** odometry or SLAM when you connect it (see `navigation_controller.py` comments)

### System Architecture
- **Edge-first services**: Python processes on the robot (`robot/perception`, `robot/control`, …) with optional cloud speech/APIs where keys and endpoints are configured
- **Telemetry**: WebSocket-style JSON channels from the mobile app (`mobile/services/json-socket.ts`) and `websockets` usage in robot perception where enabled
- **Mobile operator app**: Expo Router app under `mobile/` (camera, BLE, WiFi provisioning, status screens)
- **Mono-repo layout**: This repository holds robot, vision, navigation, and mobile sources together—**not** a separate deployed microservices cloud folder

### Performance (typical demo targets)
- **Vision rate**: Interactive frame rates from OAK-D pipelines (resolution and model dependent; validate on your Jetson)
- **Navigation loop**: Configurable update rates in `oak-navigation` controllers (see package README)
- **Latency**: Depends on model, USB, and host; profile locally rather than assuming a single published ms figure for all builds

## 📁 Repository structure

Code is grouped by **role**: shared runtime on the robot (`modules`), the **OAK-D navigation** package (`oak-navigation`), the **robot** service layout, **tests** and **models**, and the **mobile** operator app. Paths below match this repository.

```
CapstoneRoboticsProject/
├── main.py                      # Primary vision / pipeline entry
├── run_vision.py                # Alternate vision runner (camera + inference)
├── requirements.txt             # Core Python dependencies (Jetson / dev machine)
├── 99-depthai.rules             # udev rules for OAK cameras on Linux
│
├── image/                       # README and portfolio photos
├── models/                      # Neural network weights (ONNX / blobs, etc.)
├── modules/                     # Shared runtime: vision, motors, audio, rover glue
│   ├── vision.py                # RGB, depth, YOLO and related perception
│   ├── motor_control.py         # Locomotion interface
│   └── known_faces/             # Face recognition assets / data
│
├── test/                        # Vision stack tests (camera, depth, YOLO, integration)
│
├── oak-navigation/              # OAK-D navigation: depth, detection, calibration, docs
│   ├── calibration/
│   ├── depth_estimation/
│   ├── object_detection/
│   └── examples/
│
├── robot/                       # On-robot packages (perception, control, planning, localization)
│   ├── perception/              # Camera / API entrypoints for the physical platform
│   ├── control/                 # Rover control, services, bring-up and install scripts
│   ├── planning/                # High-level planning hooks (extend as needed)
│   └── localization/            # Wake word, connectivity, and supporting state logic
│
└── mobile/                      # Expo + React Native field / operator application
    ├── app/                     # Screens, routing, and app configuration
    ├── components/              # UI building blocks
    ├── services/                # APIs, device integrations, background tasks
    ├── hooks/                   # Shared UI logic
    └── context/                 # Global app state
```

**Local development:** a `depthai-env/` virtual environment and/or a `depthai-python/` SDK checkout may sit next to this tree on a workstation or Jetson; those are environment artifacts rather than the application layout above.

**Models:** the `models/` directory is **gitignored** to keep large blobs out of Git. After clone, add the YOLO / DepthAI weight files expected by `modules/vision.py` (see comments in `requirements.txt` and `vision.py`) or adjust paths for your layout.

## 🔬 Technical Challenges & Solutions

### Challenge 1: Real-time inference on edge hardware
**Problem:** Depth + detection must stay smooth on USB-attached OAK-D and a Jetson-class host.  
**Solution:** DepthAI neural blobs, tuned pipeline stages in `modules/vision.py`, and profiling on target hardware (optional PyTorch GPU paths for specific subsystems).

### Challenge 2: Depth-to-motion coupling
**Problem:** Turning dense stereo depth into safe motion commands without heavy cloud dependency.  
**Solution:** `oak-navigation/` depth processors, occupancy-style reasoning, and multiple avoidance strategies (reactive, VFH-style, potential field—see package README).

### Challenge 3: Reliable operator link
**Problem:** Field use needs discovery, BLE, WiFi setup, and optional streaming/JSON channels without a monolithic server in this repo.  
**Solution:** Expo mobile services (`mobile/services/*`) plus optional `websockets` in `robot/perception` when you wire a command server.

### Challenge 4: Dynamic environments
**Problem:** Cluttered scenes and people in-frame while the robot moves.  
**Solution:** Combine reactive avoidance with grid planners (A-star / RRT) and clear emergency-stop / recovery logic in the navigation controller.

## 🛠️ Technology Stack

### AI/ML & Computer Vision
- **Frameworks & runtimes**: Python **PyTorch** (e.g. wake-word / VAD paths), **DepthAI** for OAK pipelines and neural blobs, **OpenCV** for classic CV
- **Detection**: YOLO-style COCO detection via DepthAI blobs (see `modules/vision.py`)
- **Optimization**: Model format and resolution choices for DepthAI; further TensorRT / INT8 conversion is a **deployment option** on NVIDIA stacks, not a single pinned claim for this tree

### Robotics & Control Systems
- **Navigation code**: Custom Python in `oak-navigation/` (depth, avoidance, planning) rather than a ROS 2 package in this repository
- **Sensors**: **OAK-D** stereo depth as the primary perception input; additional sensors (e.g. LiDAR) are reflected in UI / roadmap text in places, not as a fully checked-in fusion stack
- **Control**: Shell-based bring-up under `robot/control/`, rover motion scripts, and systemd-style service files where used
- **Concurrency**: Threaded navigation / perception loops in Python where modules require it

### Software Engineering
- **Languages**: **Python** (robot, vision, navigation), **TypeScript** (Expo mobile app), **Shell** (install and device bring-up)
- **Robot-side I/O**: HTTP / WebSocket **clients** and servers in Python where enabled (`websockets` in perception); no Express server ships in this repo
- **Mobile**: **Expo SDK 54** + **React Native** (Expo Router), BLE and REST-style calls in `mobile/services/`
- **Tooling**: Git, `npm`, `pip`, and local testing under `test/`; add your own CI if you fork for production

### Hardware & Platforms
- **Edge Computing**: NVIDIA Jetson Orin (275 TOPS AI performance)
- **Sensors**: OAK-D stereo camera, IMU, encoders
- **Communication**: WiFi, Bluetooth, serial protocols
- **Embedded Systems**: Real-time Linux, device drivers

## 🎓 Capstone Project Details

### Project Scope
This capstone design project represents a comprehensive 6-month development cycle, demonstrating full-stack AI engineering capabilities from research and design to implementation and deployment.

### Development Methodology
- **Agile Development**: Iterative development with sprint-based milestones
- **MLOps Practices**: Continuous integration for model training and deployment
- **System Design**: Architecture-first approach with scalability considerations
- **Testing**: Unit tests, integration tests, and field validation

### Key Deliverables
- ✅ Integrated vision, navigation, robot, and mobile code in one capstone repository
- ✅ DepthAI + OpenCV perception path with automated tests under `test/`
- ✅ `oak-navigation/` package with documented quickstarts and integration notes
- ✅ Expo mobile application for field control and provisioning
- ✅ Per-subsystem READMEs (`oak-navigation/README.md`, `mobile/README.md`, and this file)

## 🏅 Recognition & Impact

**Best Innovation Award** — Recognized for:
- Practical edge-first perception and navigation integration on commodity stereo hardware
- Cohesive combination of vision stack, navigation module, on-robot services, and a mobile operator app
- Demonstrated systems integration suitable for capstone and portfolio review

## 💼 Skills Demonstrated

This project showcases expertise in:

- **AI/ML Engineering**: Deep learning model development, optimization, and deployment
- **Computer Vision**: Stereo depth, object detection (COCO), optional face-recognition utilities in `modules/`
- **Robotics**: Depth-based obstacle handling, classical path planning (A-star / RRT family), rover bring-up and control scripts
- **Edge Computing**: Optimizing AI models for resource-constrained devices
- **Full-Stack Development**: Python robot services, TypeScript mobile app, and HTTP/WebSocket integrations
- **System Architecture**: Modular mono-repo layout (vision, navigation, robot, mobile)
- **DevOps**: Git-based workflow; add CI/CD and containers when you promote beyond coursework
- **Problem Solving**: Tackling complex technical challenges with innovative solutions

## 🚀 Getting Started

### Prerequisites

- NVIDIA Jetson Orin Developer Kit (or compatible hardware)
- OAK-D depth camera
- Python 3.8+
- Node.js 18+ (LTS recommended; matches Expo tooling in `mobile/`)
- Optional **CUDA** GPU on a dev machine for PyTorch-heavy experiments (not required for all DepthAI-only paths)

### Installation

1. Clone this repository:
```bash
git clone https://github.com/saberabanu0001/CapstoneRoboticsProject.git
cd CapstoneRoboticsProject
```

2. Set up the **Python** environment (vision / `modules` / Jetson):
```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```
Add the DepthAI **blob** models expected under `models/` (that directory is gitignored—see `modules/vision.py` for the default filename).

3. Optional **`oak-navigation`** dependencies (see `oak-navigation/requirements.txt` and its README):
```bash
cd oak-navigation
pip install -r requirements.txt
cd ..
```

4. Install **mobile** (Expo) dependencies:
```bash
cd mobile && npm install && cd ..
```

5. On **Linux / Jetson**, install Luxonis udev rules so OAK-D enumerates reliably:
```bash
# Example: copy 99-depthai.rules per DepthAI / Luxonis documentation, then:
sudo udevadm control --reload-rules && sudo udevadm trigger
```
For **JetPack**, CUDA, and optional TensorRT on NVIDIA hardware, follow NVIDIA’s docs for your Jetson image—versions are not pinned in this README.

### Running the system

**Vision pipeline (repo root — typical for development):**
```bash
source venv/bin/activate   # if using a venv
python main.py
# or: python run_vision.py
```

**Robot perception entrypoint (when driving the on-robot stack):**
```bash
cd robot/perception
python main.py
```

**`oak-navigation` demos** (depth, avoidance, planners — see `oak-navigation/QUICKSTART.md`):
```bash
cd oak-navigation
# follow QUICKSTART / README for the specific script (e.g. test_system.py)
python test_system.py
```

**Mobile app (Expo):**
```bash
cd mobile
npm start
```
There is **no** `cloud/` service folder in this repository; any backend you use is configured via URLs and keys in the mobile app or robot code.

## 📊 Results & performance

Report numbers **after you measure on your hardware** (camera model, resolution, Jetson SKU, and USB topology dominate latency and FPS).

### What this repo is built to demonstrate
- **Vision**: OAK-D + DepthAI pipeline with COCO detection and depth preview (`modules/vision.py`, tests under `test/`)
- **Navigation**: Configurable depth-based avoidance and classical planners in `oak-navigation/`
- **Systems**: Robot bring-up scripts, perception entrypoints, and a field **Expo** app wired to the robot

### Qualitative outcomes
- End-to-end capstone story from sensing to actuation and operator UX
- Clear module boundaries for future SLAM, LiDAR fusion, or fleet backends **outside** this tree

## 🔬 Research & innovation

Themes explored in this capstone:
- Stereo-first obstacle reasoning and classical planning on edge hardware
- Practical packaging of DepthAI perception with a navigable Python stack
- Operator-centered design (mobile provisioning, status, and manual modes) alongside autonomy code

## 📚 Documentation

- This README and the **per-package** guides: `oak-navigation/README.md`, `oak-navigation/QUICKSTART.md`, `mobile/README.md`, `mobile/UI_IMPROVEMENTS.md`
- Inline module docstrings (`modules/`, `robot/`, `oak-navigation/`)
- Add your own architecture diagrams, formal API docs, and benchmark tables when you publish measured results

## 🤝 Contributing

This is a capstone project repository. For questions, suggestions, or collaboration opportunities, please open an issue or contact the maintainer.

## 📄 License

This project is shared for **educational and portfolio** use. There is **no** `LICENSE` file committed yet—add one (e.g. MIT, Apache-2.0) if you need a standard open-source grant of rights.

## 🙏 Acknowledgments

- **NVIDIA** for the Jetson Orin platform and development tools
- **Luxonis** for OAK-D camera hardware and DepthAI SDK
- **Open robotics ecosystem** (tutorials, forums, and ROS-adjacent literature) for patterns even though this repo is not a ROS 2 workspace
- **Capstone Advisors** for guidance and technical support

---

**Status**: ✅ Capstone Project Complete | 🏆 Best Innovation Award Winner

*Demonstrates hands-on work across deep learning, computer vision, edge robotics, and a shipped-style mobile app—good for portfolios in AI engineering, autonomous systems, and edge deployment.*

## 📧 Repository

- **GitHub:** [github.com/saberabanu0001/CapstoneRoboticsProject](https://github.com/saberabanu0001/CapstoneRoboticsProject)
