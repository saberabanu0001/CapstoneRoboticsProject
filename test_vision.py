from modules.vision import VisionSystem
import cv2

vision = VisionSystem()

while True:
    frame = vision.get_latest_frame()
    depth = vision.get_center_depth()

    cv2.imshow("RGB Feed", frame)

    if depth != -1:
        print(f"Center depth: {depth/1000:.2f} meters")

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cv2.destroyAllWindows()
