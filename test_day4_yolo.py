from modules.vision import VisionSystem

vision = VisionSystem(simulate=True)

for _ in range(10):
    detections = vision.get_detections_with_depth()
    if detections:
        for d in detections:
            print(f"[YOLO] {d['label']} ({d['confidence']*100:.1f}%) "
                  f"at X={d['coords_mm'][0]}mm, "
                  f"Y={d['coords_mm'][1]}mm, "
                  f"Z={d['coords_mm'][2]}mm")
