import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import TensorDataset, DataLoader
import numpy as np
import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "models")))
from hybrid_model import Hybrid3DCNN_ViT

SAVE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "saved_models"))
os.makedirs(SAVE_DIR, exist_ok=True)

def train_hybrid_model(epochs: int = 5, batch_size: int = 16):
    print("Initiating PyTorch Training Pipeline for Hybrid 3D-CNN + ViT...")
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Target Compute Device: {device}")

    # Generate synthetic calibrated training tensor patches:
    # 6 classes x 30 spatial patches = 180 patches of size (100 bands, 9x9 pixels)
    num_classes = 6
    samples_per_class = 30
    total_samples = num_classes * samples_per_class

    X = np.random.uniform(0.05, 0.65, (total_samples, 100, 9, 9)).astype(np.float32)
    y = np.zeros(total_samples, dtype=np.int64)

    for c in range(num_classes):
        start = c * samples_per_class
        end = start + samples_per_class
        y[start:end] = c
        # Distinct class spectral signatures in band channels
        if c == 1:  # Stripe Rust: depressed NIR
            X[start:end, 60:, :, :] *= 0.55
        elif c == 2:  # Mildew: elevated visible
            X[start:end, :40, :, :] += 0.15
        elif c == 3:  # Septoria: Red edge alteration
            X[start:end, 45:55, :, :] += 0.12

    # Shuffle dataset
    perm = np.random.permutation(total_samples)
    X = torch.tensor(X[perm])
    y = torch.tensor(y[perm])

    train_ds = TensorDataset(X, y)
    train_loader = DataLoader(train_ds, batch_size=batch_size, shuffle=True)

    model = Hybrid3DCNN_ViT(num_bands=100, patch_size=9, num_classes=num_classes).to(device)
    criterion = nn.CrossEntropyLoss()
    optimizer = optim.AdamW(model.parameters(), lr=0.001, weight_decay=1e-4)

    history = []
    model.train()
    for epoch in range(epochs):
        running_loss = 0.0
        correct = 0
        total = 0
        for batch_x, batch_y in train_loader:
            batch_x, batch_y = batch_x.to(device), batch_y.to(device)
            optimizer.zero_grad()
            outputs = model(batch_x)
            loss = criterion(outputs, batch_y)
            loss.backward()
            optimizer.step()

            running_loss += loss.item() * batch_x.size(0)
            _, predicted = torch.max(outputs, 1)
            total += batch_y.size(0)
            correct += (predicted == batch_y).sum().item()

        epoch_loss = running_loss / total
        epoch_acc = correct / total
        history.append({"epoch": epoch + 1, "loss": round(epoch_loss, 4), "accuracy": round(epoch_acc, 4)})
        print(f"Epoch {epoch+1}/{epochs} | Loss: {epoch_loss:.4f} | Accuracy: {epoch_acc*100:.2f}%")

    model_path = os.path.join(SAVE_DIR, "hybrid_3dcnn_vit.pt")
    torch.save(model.state_dict(), model_path)
    print(f"Model checkpoint saved successfully to: {model_path}")
    return history

if __name__ == "__main__":
    train_hybrid_model(epochs=3)

