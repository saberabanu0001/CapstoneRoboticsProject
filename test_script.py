from modules.vision import VisionSystem
import cv2

# Start VisionSystem (simulate=True until hardware arrives)
vision = VisionSystem(simulate=True)

while True:
    # --- Test 1: Latest Frame ---
    frame = vision.get_latest_frame()
    if frame is not None:
        cv2.imshow("RGB Frame", frame)

    # --- Test 2: Center Depth ---
    depth = vision.get_center_depth()
    if depth is not None:
        print(f"[Depth] Center depth: {depth:.2f} meters")

    # --- Test 3: YOLO Detections + Depth ---
    detections = vision.get_detections_with_depth()
    if detections:
        for d in detections:
            print(f"[YOLO] {d['label']} ({d['confidence']*100:.1f}%) "
                  f"at X={d['coords_mm'][0]}mm, "
                  f"Y={d['coords_mm'][1]}mm, "
                  f"Z={d['coords_mm'][2]}mm")

    # Quit loop with 'q'
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cv2.destroyAllWindows()
