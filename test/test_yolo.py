from modules.vision import VisionSystem

vision = VisionSystem(simulate=True)
detections = vision.get_detections_with_depth()
for d in detections:
    print(f"[YOLO] {d['label']} ({d['confidence']*100:.1f}%)", end="")
    if 'x' in d and 'y' in d and 'z' in d:
        print(f" at X={d['x']}mm, Y={d['y']}mm, Z={d['z']}mm")
    else:
        print(" (no depth data available)")

    

