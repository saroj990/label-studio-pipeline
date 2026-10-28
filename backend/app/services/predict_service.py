from __future__ import annotations

from pathlib import Path

import torch
import torch.nn as nn
from PIL import Image, ImageOps
from torchvision import models, transforms


def predict_image(model_path: Path, image_path: Path) -> tuple[str, dict[str, float]]:
    device = torch.device("cpu")

    checkpoint = torch.load(model_path, map_location="cpu", weights_only=True)
    classes = checkpoint["classes"]

    model = models.mobilenet_v3_small(weights=None)
    model.classifier[3] = nn.Linear(
        model.classifier[3].in_features,
        len(classes),
    )
    model.load_state_dict(checkpoint["state_dict"])
    model = model.to(device)
    model.eval()

    preprocess = transforms.Compose([
        transforms.Resize((224, 224)),
        transforms.ToTensor(),
        transforms.Normalize(
            mean=[0.485, 0.456, 0.406],
            std=[0.229, 0.224, 0.225],
        ),
    ])

    with Image.open(image_path) as source:
        image = ImageOps.exif_transpose(source).convert("RGB")

    tensor = preprocess(image).unsqueeze(0).to(device)

    with torch.no_grad():
        probabilities = torch.softmax(model(tensor), dim=1)[0]

    predicted_index = int(probabilities.argmax().item())
    scores = {
        name: float(probabilities[index].item())
        for index, name in enumerate(classes)
    }
    return classes[predicted_index], scores
