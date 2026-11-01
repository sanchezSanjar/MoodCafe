"""Measure the expression model on FER-2013 test faces, with focus on "happy" (the discount trigger).

Run:  .venv\\Scripts\\python.exe scripts\\evaluate.py [--limit 2000]
Writes docs/evaluation.json.
"""
import argparse
import json
import sys
import time
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from moodcafe.config import ROOT  # noqa: E402
from moodcafe.expression import EXPRESSIONS, ExpressionClassifier  # noqa: E402

DATASET = "AutumnQiu/fer2013"  # official FER-2013 splits; "test" = PrivateTest (3,589 faces)
HAPPY = EXPRESSIONS.index("happy")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=0, help="number of test faces (0 = all)")
    parser.add_argument("--batch", type=int, default=64)
    args = parser.parse_args()

    from datasets import load_dataset
    rows = load_dataset(DATASET, split="test")
    if args.limit:
        rows = rows.shuffle(seed=0).select(range(args.limit))
    classifier = ExpressionClassifier()

    truth, predicted, happy_scores = [], [], []
    started = time.perf_counter()
    for start in range(0, len(rows), args.batch):
        batch = rows[start:start + args.batch]
        faces = [cv2.cvtColor(np.array(img.convert("RGB")), cv2.COLOR_RGB2BGR) for img in batch["image"]]
        for probs, label in zip(classifier.predict(faces), batch["label"]):
            truth.append(label)
            predicted.append(int(np.argmax([probs[e] for e in EXPRESSIONS])))
            happy_scores.append(probs["happy"])
    seconds = time.perf_counter() - started

    truth, predicted, happy_scores = map(np.array, (truth, predicted, happy_scores))
    per_class = {name: round(float((predicted[truth == i] == i).mean()), 3)
                 for i, name in enumerate(EXPRESSIONS) if (truth == i).any()}
    is_happy = truth == HAPPY
    thresholds = {}
    for threshold in (0.5, 0.7, 0.8, 0.9):
        flagged = happy_scores >= threshold
        thresholds[str(threshold)] = {
            "smiles_caught": round(float(flagged[is_happy].mean()), 3),          # recall
            "non_smiles_flagged": round(float(flagged[~is_happy].mean()), 3),    # false positive rate
            "precision": round(float(is_happy[flagged].mean()), 3) if flagged.any() else None,
        }
    result = {
        "dataset": f"{DATASET} (test split)",
        "faces": int(len(truth)),
        "accuracy_7_expressions": round(float((truth == predicted).mean()), 3),
        "accuracy_per_expression": per_class,
        "happy_threshold": thresholds,
        "ms_per_face": round(1000 * seconds / len(truth), 2),
        "device": classifier.device_name,
    }
    (ROOT / "docs").mkdir(exist_ok=True)
    (ROOT / "docs" / "evaluation.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
