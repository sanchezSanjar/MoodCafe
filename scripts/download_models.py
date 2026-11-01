"""One-time download of the face detector and expression model into models/ (needs internet)."""
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from moodcafe.config import (EXPRESSION_MODEL_DIR, EXPRESSION_MODEL_ID, FACE_MODEL,  # noqa: E402
                             FACE_MODEL_URL, MODELS_DIR)


def main():
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    if not FACE_MODEL.exists():
        print(f"Downloading YuNet face detector -> {FACE_MODEL}")
        urllib.request.urlretrieve(FACE_MODEL_URL, FACE_MODEL)

    from huggingface_hub import snapshot_download
    print(f"Downloading {EXPRESSION_MODEL_ID} -> {EXPRESSION_MODEL_DIR}")
    snapshot_download(repo_id=EXPRESSION_MODEL_ID, local_dir=str(EXPRESSION_MODEL_DIR),
                      allow_patterns=["config.json", "preprocessor_config.json", "model.safetensors"])
    print("Done. Mood Cafe now works offline.")


if __name__ == "__main__":
    main()
