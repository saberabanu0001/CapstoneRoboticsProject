from modules.vision import VisionSystem

vision = VisionSystem(simulate=True)
detections = vision.get_detections_with_depth()

for d in detections:
    x, y, z = d["coords_mm"]
    print(f"[YOLO] {d['label']} ({d['confidence']*100:.1f}%) "
          f"at X={x}mm, Y={y}mm, Z={z}mm")
