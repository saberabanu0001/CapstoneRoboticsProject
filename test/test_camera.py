from modules.vision import VisionSystem

vision = VisionSystem(simulate=True)
frame = vision.get_latest_frame()
if frame is not None:
    print("[TEST] RGB frame captured successfully!")
else:
    print("[TEST] No frame received.")
