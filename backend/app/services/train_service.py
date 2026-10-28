from __future__ import annotations

from pathlib import Path

import torch
import torch.nn as nn
from torch.utils.data import DataLoader
from torchvision import datasets, models, transforms
from torchvision.models import MobileNet_V3_Small_Weights


def get_device() -> torch.device:
    if torch.backends.mps.is_available():
        return torch.device("mps")
    if torch.cuda.is_available():
        return torch.device("cuda")
    return torch.device("cpu")


def train_image_folder(
    dataset_dir: Path,
    out_path: Path,
    epochs: int = 15,
) -> dict:
    device = get_device()

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

    dataset = datasets.ImageFolder(dataset_dir, transform=train_transform)
    if len(dataset.classes) != 2:
        raise ValueError("Expected exactly two classes in dataset folder.")

    counts = {name: 0 for name in dataset.classes}
    for _, class_id in dataset.samples:
        counts[dataset.classes[class_id]] += 1

    if min(counts.values()) < 2:
        raise ValueError("Need at least two images per class to train.")

    loader = DataLoader(
        dataset,
        batch_size=min(4, len(dataset)),
        shuffle=True,
        num_workers=0,
    )

    model = models.mobilenet_v3_small(weights=MobileNet_V3_Small_Weights.DEFAULT)
    for parameter in model.parameters():
        parameter.requires_grad = False

    input_features = model.classifier[3].in_features
    model.classifier[3] = nn.Linear(input_features, len(dataset.classes))
    model = model.to(device)

    criterion = nn.CrossEntropyLoss()
    optimizer = torch.optim.Adam(model.classifier[3].parameters(), lr=0.001)

    final_loss = 0.0
    final_accuracy = 0.0

    for _epoch in range(epochs):
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

        final_loss = total_loss / seen if seen else 0.0
        final_accuracy = 100 * correct / seen if seen else 0.0

    out_path.parent.mkdir(parents=True, exist_ok=True)
    torch.save(
        {
            "state_dict": model.cpu().state_dict(),
            "classes": dataset.classes,
        },
        out_path,
    )

    return {
        "device": str(device),
        "classes": dataset.classes,
        "counts": counts,
        "epochs": epochs,
        "final_loss": round(final_loss, 4),
        "training_accuracy": round(final_accuracy, 1),
    }
