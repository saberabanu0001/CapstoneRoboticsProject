from modules.vision import VisionSystem

vision = VisionSystem(simulate=True)

print("\n[TEST] Running full VisionSystem integration...")
frame = vision.get_latest_frame()
depth = vision.get_center_depth()
detections = vision.get_detections_with_depth()

print(f"Frame captured: {frame is not None}")
print(f"Center depth: {depth:.2f} meters")
print(f"Detections: {len(detections)} found")
