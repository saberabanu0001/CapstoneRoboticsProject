import cv2
import torch
from transformers import AutoProcessor, AutoModelForVision2Seq
from PIL import Image
import depthai as dai

# -----------------------------
# CONFIGURATION
# -----------------------------
USE_OAKD = True  # ✅ Set to True for OptiCamera (OAK-D), False for MacBook webcam
MODEL_NAME = "Salesforce/blip-image-captioning-base"

# -----------------------------
# LOAD THE VISION-LANGUAGE MODEL
# -----------------------------
print("🧠 Loading Vision-Language Model...")
processor = AutoProcessor.from_pretrained(MODEL_NAME)
model = AutoModelForVision2Seq.from_pretrained(MODEL_NAME)
device = "cuda" if torch.cuda.is_available() else "cpu"
model.to(device)
print("✅ Model loaded successfully on", device.upper())

# -----------------------------
# SETUP CAMERA (OAK-D OR WEBCAM)
# -----------------------------
if USE_OAKD:
    # OAK-D pipeline setup
    pipeline = dai.Pipeline()
    cam_rgb = pipeline.create(dai.node.ColorCamera)
    cam_rgb.setPreviewSize(640, 480)
    cam_rgb.setInterleaved(False)
    xout_rgb = pipeline.create(dai.node.XLinkOut)
    xout_rgb.setStreamName("rgb")
    cam_rgb.preview.link(xout_rgb.input)
    device_oak = dai.Device(pipeline)
    q_rgb = device_oak.getOutputQueue(name="rgb", maxSize=1, blocking=False)
    print("🎥 OAK-D Camera connected.")
else:
    cap = cv2.VideoCapture(0)
    print("🎥 MacBook webcam connected.")

# -----------------------------
# MAIN LOOP
# -----------------------------
print("\n🚀 Vision-Language Live Captioning Started (press 'q' to quit)")
frame_count = 0

while True:
    # Capture frame from camera
    if USE_OAKD:
        in_rgb = q_rgb.tryGet()
        if in_rgb is None:
            continue
        frame = in_rgb.getCvFrame()
    else:
        ret, frame = cap.read()
        if not ret:
            break

    frame_count += 1

    # Process one frame every 60 frames (~2 seconds)
    if frame_count % 60 == 0:
        img = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        inputs = processor(images=img, return_tensors="pt").to(device)

        with torch.no_grad():
            out = model.generate(**inputs, max_new_tokens=20)

        caption = processor.batch_decode(out, skip_special_tokens=True)[0]
        print(f"🧠 {caption}")

        # Display caption on screen
        cv2.putText(frame, caption, (20, 40),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 0), 2)

    cv2.imshow("VLM Camera Captioning", frame)

    # Quit when 'q' pressed
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

# -----------------------------
# CLEANUP
# -----------------------------
if not USE_OAKD:
    cap.release()
cv2.destroyAllWindows()
print("🛑 Stream stopped successfully.")
