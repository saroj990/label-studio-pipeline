"""Train a two-class MobileNet V3 classifier on cli/dataset/."""

from __future__ import annotations

from pathlib import Path

import torch
import torch.nn as nn
from torch.utils.data import DataLoader
from torchvision import datasets, models, transforms
from torchvision.models import MobileNet_V3_Small_Weights

SCRIPT_DIR = Path(__file__).resolve().parent
DATASET = SCRIPT_DIR / "dataset"
MODEL_PATH = SCRIPT_DIR / "model.pth"


def get_device() -> torch.device:
    if torch.backends.mps.is_available():
        return torch.device("mps")
    if torch.cuda.is_available():
        return torch.device("cuda")
    return torch.device("cpu")


if not DATASET.is_dir() or len(list(DATASET.iterdir())) < 2:
    raise SystemExit("Run prepare_dataset.py first (need cli/dataset with two class folders).")

device = get_device()
print("Training device:", device)

train_transform = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.RandomRotation(5),
    transforms.ColorJitter(brightness=0.15, contrast=0.15),
    transforms.ToTensor(),
    transforms.Normalize(
        mean=[0.485, 0.456, 0.406],
        std=[0.229, 0.224, 0.225],
    ),
])

dataset = datasets.ImageFolder(DATASET, transform=train_transform)

if len(dataset) < 2 or len(dataset.classes) != 2:
    raise SystemExit("Expected exactly two class folders under cli/dataset/.")

counts = {name: 0 for name in dataset.classes}
for _, class_id in dataset.samples:
    counts[dataset.classes[class_id]] += 1

print("Classes:", dataset.classes)
print("Images:", counts)

if min(counts.values()) < 2:
    raise SystemExit("Provide at least two images in each class.")

loader = DataLoader(
    dataset,
    batch_size=min(4, len(dataset)),
    shuffle=True,
    num_workers=0,
)

weights = MobileNet_V3_Small_Weights.DEFAULT
model = models.mobilenet_v3_small(weights=weights)

for parameter in model.parameters():
    parameter.requires_grad = False

input_features = model.classifier[3].in_features
model.classifier[3] = nn.Linear(input_features, len(dataset.classes))
model = model.to(device)

criterion = nn.CrossEntropyLoss()
optimizer = torch.optim.Adam(model.classifier[3].parameters(), lr=0.001)

epochs = 15

for epoch in range(epochs):
    model.train()
    total_loss = 0.0
    correct = 0
    seen = 0

    for images, labels in loader:
        images = images.to(device)
        labels = labels.to(device)

        optimizer.zero_grad()
        outputs = model(images)
        loss = criterion(outputs, labels)
        loss.backward()
        optimizer.step()

        total_loss += loss.item() * labels.size(0)
        correct += (outputs.argmax(1) == labels).sum().item()
        seen += labels.size(0)

    print(
        f"Epoch {epoch + 1:02d}/{epochs} "
        f"loss={total_loss / seen:.4f} "
        f"training_accuracy={100 * correct / seen:.1f}%"
    )

torch.save(
    {
        "state_dict": model.cpu().state_dict(),
        "classes": dataset.classes,
    },
    MODEL_PATH,
)

print(f"\nSaved model to: {MODEL_PATH}")
print("Training accuracy on labeled photos is not the same as performance on new images.")
