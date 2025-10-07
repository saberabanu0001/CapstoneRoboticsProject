import depthai as dai
import cv2
import numpy as np
import random


class VisionSystem:
    def __init__(self, simulate=False):
        self.simulate = simulate

        if not self.simulate:
            try:
                # Create pipeline
                self.pipeline = dai.Pipeline()

                # RGB camera
                cam_rgb = self.pipeline.create(dai.node.ColorCamera)
                cam_rgb.setPreviewSize(416, 416)   # YOLO input size
                cam_rgb.setInterleaved(False)

                # Mono + stereo depth
                mono_left = self.pipeline.create(dai.node.MonoCamera)
                mono_right = self.pipeline.create(dai.node.MonoCamera)
                stereo = self.pipeline.create(dai.node.StereoDepth)
                mono_left.setBoardSocket(dai.CameraBoardSocket.LEFT)
                mono_right.setBoardSocket(dai.CameraBoardSocket.RIGHT)

                # YOLO Spatial Detection
                detection_nn = self.pipeline.create(dai.node.YoloSpatialDetectionNetwork)
                detection_nn.setBlobPath("yolo-v4-tiny_openvino_2021.4_6shave.blob")
                detection_nn.setConfidenceThreshold(0.5)

                # YOLO params
                detection_nn.setNumClasses(80)
                detection_nn.setCoordinateSize(4)
                detection_nn.setAnchors([
                    10,14, 23,27, 37,58,
                    81,82, 135,169, 344,319
                ])
                detection_nn.setAnchorMasks({
                    "side26": [1,2,3],
                    "side13": [3,4,5]
                })
                detection_nn.setIouThreshold(0.5)

                # Outputs
                xout_rgb = self.pipeline.create(dai.node.XLinkOut)
                xout_nn = self.pipeline.create(dai.node.XLinkOut)
                xout_depth = self.pipeline.create(dai.node.XLinkOut)

                xout_rgb.setStreamName("rgb")
                xout_nn.setStreamName("detections")
                xout_depth.setStreamName("depth")

                # Linking
                cam_rgb.preview.link(detection_nn.input)
                mono_left.out.link(stereo.left)
                mono_right.out.link(stereo.right)
                stereo.depth.link(detection_nn.inputDepth)
                detection_nn.passthrough.link(xout_rgb.input)
                detection_nn.out.link(xout_nn.input)
                stereo.depth.link(xout_depth.input)

                # Connect device
                self.device = dai.Device(self.pipeline)
                self.q_rgb = self.device.getOutputQueue("rgb", maxSize=4, blocking=False)
                self.q_det = self.device.getOutputQueue("detections", maxSize=4, blocking=False)
                self.q_depth = self.device.getOutputQueue("depth", maxSize=4, blocking=False)

            except RuntimeError:
                print("⚠️ No OAK-D device found → Switching to simulation mode.")
                self.simulate = True

    # --- Day-2 ---
    def get_latest_frame(self):
        if self.simulate:
            return np.zeros((416, 416, 3), dtype=np.uint8)
        in_rgb = self.q_rgb.tryGet()
        if in_rgb is not None:
            return in_rgb.getCvFrame()
        return None

    # --- Day-3 ---
    def get_center_depth(self):
        if self.simulate:
            return round(random.uniform(0.5, 3.0), 2)  # meters
        in_depth = self.q_depth.tryGet()
        if in_depth is not None:
            depth_frame = in_depth.getFrame()
            h, w = depth_frame.shape
            center = depth_frame[h//2, w//2]
            return center / 1000.0  # mm → meters
        return None

    # --- Day-4 ---
    def get_detections_with_depth(self):
        if self.simulate:
            labels = ["person", "dog", "car", "box"]
            detections = []
            for _ in range(random.randint(0, 3)):
                detections.append({
                    "label": random.choice(labels),
                    "confidence": round(random.uniform(0.6, 0.95), 2),
                    "bbox": [50, 50, 200, 200],
                    "coords_mm": (
                        random.randint(-100, 100),
                        random.randint(-100, 100),
                        random.randint(500, 3000)
                    )
                })
            return detections

        in_det = self.q_det.tryGet()
        detections = []
        if in_det is not None:
            for det in in_det.detections:
                detections.append({
                    "label": det.label,
                    "confidence": det.confidence,
                    "bbox": [det.xmin, det.ymin, det.xmax, det.ymax],
                    "coords_mm": (
                        det.spatialCoordinates.x,
                        det.spatialCoordinates.y,
                        det.spatialCoordinates.z
                    )
                })
        return detections

    # --- Simulation Mode (Webcam + Dummy Detection) ---
    def run_simulation(self):
        print("🎥 Starting webcam simulation... Press 'q' to quit.")
        cap = cv2.VideoCapture(0)

        if not cap.isOpened():
            print("⚠️ Webcam not available. Exiting simulation.")
            return

        labels = ["person", "car", "dog", "bottle"]

        while True:
            ret, frame = cap.read()
            if not ret:
                print("⚠️ Failed to capture frame.")
                break

            # Draw random dummy detections
            for _ in range(random.randint(1, 3)):
                x1, y1 = random.randint(50, 200), random.randint(50, 200)
                x2, y2 = x1 + random.randint(100, 200), y1 + random.randint(100, 200)
                label = random.choice(labels)
                color = (0, 255, 0)
                cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
                cv2.putText(frame, label, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

            # Show window
            cv2.imshow("Dummy Vision - Webcam", frame)

            # Exit on 'q'
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

        cap.release()
        cv2.destroyAllWindows()
        print("✅ Simulation ended.")

    def detect_person_simulation(self):
    print("🧍 Person Detection (Simulation) - Press 'q' to quit.")
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("⚠️ Webcam not found.")
        return

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        # Simulate random 'person' detections
        for _ in range(random.randint(0, 2)):
            x1, y1 = random.randint(50, 300), random.randint(50, 300)
            x2, y2 = x1 + random.randint(100, 200), y1 + random.randint(150, 250)
            color = (0, 255, 0)
            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
            cv2.putText(frame, "person", (x1, y1 - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

        cv2.imshow("Person Detection Simulation", frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    VisionSystem(simulate=True).run_simulation()
