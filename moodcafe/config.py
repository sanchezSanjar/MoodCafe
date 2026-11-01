"""Paths and constants shared by the app and tools."""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MODELS_DIR = ROOT / "models"

FACE_MODEL = MODELS_DIR / "face_detection_yunet.onnx"
FACE_MODEL_URL = ("https://github.com/opencv/opencv_zoo/raw/main/models/"
                  "face_detection_yunet/face_detection_yunet_2023mar.onnx")

# Pretrained ViT expression model, fine-tuned on FER-2013 (Apache-2.0)
EXPRESSION_MODEL_ID = "abhilash88/face-emotion-detection"
EXPRESSION_MODEL_DIR = MODELS_DIR / "expression"

COUPONS_FILE = ROOT / "coupons.csv"
