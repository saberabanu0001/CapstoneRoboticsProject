import face_recognition
import cv2
import os
import numpy as np

class FaceRecognition:
    def __init__(self, known_dir="modules/known_faces"):
        self.known_encodings = []
        self.known_names = []
        self.load_known_faces(known_dir)

    def load_known_faces(self, folder):
        """Load all known faces and their names"""
        for filename in os.listdir(folder):
            if filename.endswith(".jpg") or filename.endswith(".png"):
                path = os.path.join(folder, filename)
                name = os.path.splitext(filename)[0]
                image = face_recognition.load_image_file(path)
                encoding = face_recognition.face_encodings(image)
                if encoding:
                    self.known_encodings.append(encoding[0])
                    self.known_names.append(name)
                    print(f"✅ Loaded face: {name}")

    def recognize_face(self, frame):
        """Detect and recognize faces from the frame"""
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        face_locations = face_recognition.face_locations(rgb_frame)
        face_encodings = face_recognition.face_encodings(rgb_frame, face_locations)

        matches = []
        for (top, right, bottom, left), face_encoding in zip(face_locations, face_encodings):
            name = "Unknown"
            distances = face_recognition.face_distance(self.known_encodings, face_encoding)
            if len(distances) > 0:
                best_match_index = np.argmin(distances)
                if distances[best_match_index] < 0.45:
                    name = self.known_names[best_match_index]

            matches.append((name, (left, top, right, bottom)))
        return matches
