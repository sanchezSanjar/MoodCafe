"""Face detection with OpenCV: YuNet (deep learning) or the classic Haar cascade as fallback."""
from dataclasses import dataclass

import cv2

from .config import FACE_MODEL


@dataclass
class Face:
    x: int
    y: int
    w: int
    h: int
    score: float

    @property
    def area(self):
        return self.w * self.h

    def crop(self, frame, margin=0.2):
        """Face region with some margin, clipped to the frame."""
        dx, dy = int(self.w * margin), int(self.h * margin)
        height, width = frame.shape[:2]
        x0, y0 = max(0, self.x - dx), max(0, self.y - dy)
        x1, y1 = min(width, self.x + self.w + dx), min(height, self.y + self.h + dy)
        return frame[y0:y1, x0:x1]


class FaceDetector:
    def __init__(self, min_score=0.8):
        self.min_score = min_score
        if FACE_MODEL.exists():
            self.kind = "YuNet"
            self._yunet = cv2.FaceDetectorYN.create(str(FACE_MODEL), "", (320, 320), min_score)
        else:
            self.kind = "Haar cascade"
            self._haar = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")

    def detect(self, frame):
        """All faces in a BGR frame, largest first."""
        if self.kind == "YuNet":
            height, width = frame.shape[:2]
            self._yunet.setInputSize((width, height))
            _, rows = self._yunet.detect(frame)
            faces = [] if rows is None else [
                Face(int(r[0]), int(r[1]), int(r[2]), int(r[3]), float(r[14])) for r in rows]
        else:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            boxes = self._haar.detectMultiScale(gray, 1.1, 5, minSize=(60, 60))
            faces = [Face(int(x), int(y), int(w), int(h), 1.0) for x, y, w, h in boxes]
        faces = [f for f in faces if f.w > 0 and f.h > 0]
        return sorted(faces, key=lambda f: f.area, reverse=True)
