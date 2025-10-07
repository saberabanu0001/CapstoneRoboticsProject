from modules.vision import VisionSystem

print("🔹 Starting Vision Module Test...")

vision = VisionSystem()   # create the object

for i in range(5):
    frame = vision.get_latest_frame()
    if frame is not None:
        print(f"[{i}] Frame captured:", frame.shape)
    else:
        print(f"[{i}] No frame captured")

    print("Person detected:", vision.is_person_detected())
    print("Obstacle distance:", f"{vision.get_obstacle_distance():.2f} m")
    print("----")

vision.cleanup()
print("✅ Vision module test complete.")
