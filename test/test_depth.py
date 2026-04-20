from modules.vision import VisionSystem

vision = VisionSystem(simulate=True)
depth = vision.get_center_depth()
print(f"[TEST] Center depth: {depth:.2f} meters")
