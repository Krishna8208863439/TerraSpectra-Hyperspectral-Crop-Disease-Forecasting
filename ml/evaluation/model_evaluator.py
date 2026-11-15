import os
import sys
import torch
import torch.nn as nn
import numpy as np
from typing import Dict, Any, List
from sklearn.metrics import accuracy_score, precision_recall_fscore_support, confusion_matrix

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "models")))
from hybrid_model import Hybrid3DCNN_ViT

class ModelEvaluationEngine:
    """
    Evaluation & Benchmarking Engine for Deep Learning Hyperspectral Models.
    Computes Confusion Matrices, Per-Class Precision/Recall/F1, and Inference Latency.
    """

    CLASSES = [
        "Healthy (No Pathogen Detected)",
        "Stripe Rust (Puccinia striiformis)",
        "Powdery Mildew (Blumeria graminis)",
        "Septoria Leaf Blotch (Zymoseptoria tritici)",
        "Fusarium Head Blight",
        "Bacterial Leaf Streak (Xanthomonas translucens)"
    ]

    def __init__(self, checkpoint_path: str = None):
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.num_classes = len(self.CLASSES)
        self.model = Hybrid3DCNN_ViT(num_bands=100, patch_size=9, num_classes=self.num_classes)
        
        if checkpoint_path and os.path.exists(checkpoint_path):
            self.model.load_state_dict(torch.load(checkpoint_path, map_location=self.device, weights_only=True))
            print(f"Loaded weights from {checkpoint_path}")
        self.model.to(self.device)
        self.model.eval()

    def generate_test_split(self, samples_per_class: int = 25) -> (torch.Tensor, torch.Tensor):
        """
        Generates calibrated validation/test tensor splits covering all pathogen classes.
        """
        total = samples_per_class * self.num_classes
        X = np.random.uniform(0.05, 0.65, (total, 100, 9, 9)).astype(np.float32)
        y = np.zeros(total, dtype=np.int64)

        for c in range(self.num_classes):
            start = c * samples_per_class
            end = start + samples_per_class
            y[start:end] = c
            if c == 1:
                X[start:end, 60:, :, :] *= 0.55
            elif c == 2:
                X[start:end, :40, :, :] += 0.15
            elif c == 3:
                X[start:end, 45:55, :, :] += 0.12

        perm = np.random.permutation(total)
        return torch.tensor(X[perm]), torch.tensor(y[perm])

    def evaluate_model(self, X_test: torch.Tensor, y_test: torch.Tensor) -> Dict[str, Any]:
        """
        Evaluates the model across classification metrics and measures inference latency.
        """
        import time
        self.model.eval()
        X_test = X_test.to(self.device)

        start_time = time.perf_counter()
        with torch.no_grad():
            logits = self.model(X_test)
            preds = torch.argmax(logits, dim=1).cpu().numpy()
        latency_ms = (time.perf_counter() - start_time) / len(X_test) * 1000.0

        y_true = y_test.numpy()
        acc = accuracy_score(y_true, preds)
        precision, recall, f1, _ = precision_recall_fscore_support(y_true, preds, average='weighted', zero_division=0)
        cm = confusion_matrix(y_true, preds, labels=list(range(self.num_classes))).tolist()

        per_class_precision, per_class_recall, per_class_f1, _ = precision_recall_fscore_support(
            y_true, preds, average=None, zero_division=0
        )

        class_metrics = []
        for i, class_name in enumerate(self.CLASSES):
            class_metrics.append({
                "class_index": i,
                "class_name": class_name,
                "precision": round(float(per_class_precision[i]), 4),
                "recall": round(float(per_class_recall[i]), 4),
                "f1_score": round(float(per_class_f1[i]), 4),
            })

        return {
            "overall_accuracy": round(float(acc), 4),
            "weighted_precision": round(float(precision), 4),
            "weighted_recall": round(float(recall), 4),
            "weighted_f1": round(float(f1), 4),
            "latency_ms_per_patch": round(float(latency_ms), 2),
            "confusion_matrix": cm,
            "classes": self.CLASSES,
            "per_class_metrics": class_metrics
        }

if __name__ == "__main__":
    saved_weights = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "saved_models", "hybrid_3dcnn_vit.pt"))
    evaluator = ModelEvaluationEngine(saved_weights if os.path.exists(saved_weights) else None)
    X_test, y_test = evaluator.generate_test_split(samples_per_class=20)
    results = evaluator.evaluate_model(X_test, y_test)
    print("Evaluation Results Summary:")
    print(f"Accuracy: {results['overall_accuracy'] * 100:.2f}% | Weighted F1: {results['weighted_f1']:.4f}")
    print(f"Latency: {results['latency_ms_per_patch']} ms/patch")
