"""Paths and constants shared by the app, training and tools."""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MODELS_DIR = ROOT / "models"
FACE_MODEL = MODELS_DIR / "face_detection_yunet.onnx"
FACE_MODEL_URL = ("https://github.com/opencv/opencv_zoo/raw/main/models/"
                  "face_detection_yunet/face_detection_yunet_2023mar.onnx")
EXPRESSION_MODEL = MODELS_DIR / "expression_mobilenetv2.pt"
DATA_DIR = ROOT / "data" / "fer2013"
COUPONS_FILE = ROOT / "coupons.csv"

# FER-2013 expression order (same as the dataset labels)
EXPRESSIONS = ["angry", "disgust", "fear", "happy", "sad", "surprise", "neutral"]
HAPPY = EXPRESSIONS.index("happy")
IMAGE_SIZE = 96  # face crops are resized to IMAGE_SIZE x IMAGE_SIZE
