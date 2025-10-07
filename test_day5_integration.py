from modules.vision import VisionSystem
import cv2

# Start in simulation mode (set False when hardware arrives)
vision = VisionSystem(simulate=True)

while True:
    # 1. Get RGB frame
    frame = vision.get_latest_frame()

    # 2. Get center depth
    depth = vision.get_center_depth()

    # 3. Get YOLO detections with depth
    detections = vision.get_detections_with_depth()

    # 4. Draw results (only if we have a frame)
    if frame is not None:
        if detections:
            for d in detections:
                x1, y1, x2, y2 = d["bbox"]
                label = f"{d['label']} {d['confidence']*100:.1f}%"
                depth_info = f"Z={d['coords_mm'][2]}mm"

                # Draw bounding box
                cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                cv2.putText(frame, label, (x1, y1 - 10),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
                cv2.putText(frame, depth_info, (x1, y2 + 20),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 2)

        # Show center depth in corner
        if depth is not None:
            cv2.putText(frame, f"Center depth: {depth:.2f}m",
                        (20, 30), cv2.FONT_HERSHEY_SIMPLEX,
                        0.7, (0, 0, 255), 2)

        cv2.imshow("Day-5 Integration Test", frame)

    # Quit with 'q'
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cv2.destroyAllWindows()
