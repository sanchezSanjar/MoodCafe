"""Facial expression classifier (ViT fine-tuned on FER-2013), runs on the GPU when available."""
import cv2
import numpy as np

from .config import EXPRESSION_MODEL_DIR

# Label order of the model (FER-2013 order): LABEL_0 = angry ... LABEL_6 = neutral
EXPRESSIONS = ["angry", "disgust", "fear", "happy", "sad", "surprise", "neutral"]


class ExpressionClassifier:
    def __init__(self, model_dir=EXPRESSION_MODEL_DIR):
        import torch
        from transformers import ViTForImageClassification, ViTImageProcessor

        if not (model_dir / "model.safetensors").exists():
            raise FileNotFoundError("Expression model missing. Run INSTALL_WINDOWS.bat once while online.")
        self._torch = torch
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        dtype = torch.float16 if self.device == "cuda" else torch.float32
        self.processor = ViTImageProcessor.from_pretrained(str(model_dir))
        self.model = ViTForImageClassification.from_pretrained(str(model_dir), dtype=dtype).to(self.device).eval()

    @property
    def device_name(self):
        if self.device == "cuda":
            return self._torch.cuda.get_device_name(0)
        return "CPU"

    def predict(self, faces_bgr):
        """Expression probabilities for a list of BGR face crops -> list of {expression: probability}."""
        if not faces_bgr:
            return []
        # FER-2013 faces are grayscale; converting keeps webcam colour from confusing the model.
        images = [cv2.cvtColor(cv2.cvtColor(face, cv2.COLOR_BGR2GRAY), cv2.COLOR_GRAY2RGB) for face in faces_bgr]
        inputs = self.processor(images=images, return_tensors="pt").to(self.device, self.model.dtype)
        with self._torch.inference_mode():
            probs = self._torch.softmax(self.model(**inputs).logits.float(), dim=-1).cpu().numpy()
        return [dict(zip(EXPRESSIONS, row.astype(np.float64))) for row in probs]
