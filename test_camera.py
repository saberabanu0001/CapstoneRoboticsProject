#!/usr/bin/env python3

import cv2
import depthai as dai

# Step 1: Create a pipeline
pipeline = dai.Pipeline()

# Step 2: Define the camera source and output
camRgb = pipeline.create(dai.node.ColorCamera)
xout = pipeline.create(dai.node.XLinkOut)

xout.setStreamName("rgb")

# Configure the camera
camRgb.setPreviewSize(300, 300)
camRgb.setInterleaved(False)
camRgb.setFps(30)

# Link camera output to XLinkOut
camRgb.preview.link(xout.input)

# Step 3: Connect to device and start the pipeline
with dai.Device(pipeline) as device:
    # Get output queue
    q = device.getOutputQueue(name="rgb")

    while True:
        inFrame = q.get()  # Get the latest frame
        frame = inFrame.getCvFrame()  # Convert to OpenCV format

        cv2.imshow("Test Camera", frame)

        if cv2.waitKey(1) == ord('q'):
            break
