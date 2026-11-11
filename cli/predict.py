"""Score one image with cli/model.pth."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import torch
import torch.nn as nn
from PIL import Image, ImageOps
from torchvision import models, transforms

SCRIPT_DIR = Path(__file__).resolve().parent


def get_device() -> torch.device:
    if torch.backends.mps.is_available():
        return torch.device("mps")
    if torch.cuda.is_available():
        return torch.device("cuda")
    return torch.device("cpu")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("image", type=Path, help="Path to a JPG/PNG page photo")
    parser.add_argument(
        "--model",
        type=Path,
        default=SCRIPT_DIR / "model.pth",
        help="Checkpoint from train.py (default: cli/model.pth)",
    )
    args = parser.parse_args()

    image_path = args.image.expanduser()
    if not image_path.is_file():
        raise SystemExit(f"Image not found: {image_path}")
    if not args.model.is_file():
        raise SystemExit(f"Model not found: {args.model} (run train.py first)")

    device = get_device()
    checkpoint = torch.load(args.model, map_location="cpu", weights_only=True)
    classes = checkpoint["classes"]

    model = models.mobilenet_v3_small(weights=None)
    model.classifier[3] = nn.Linear(model.classifier[3].in_features, len(classes))
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

    print(f"\nImage: {image_path.name}")
    print(f"Prediction: {classes[predicted_index]}")
    print("Scores:")
    for index, name in enumerate(classes):
        print(f"  {name}: {probabilities[index].item() * 100:.1f}%")
    print("\nScores are model outputs, not calibrated confidence.")


if __name__ == "__main__":
    try:
        main()
    except SystemExit as exc:
        if exc.code:
            sys.exit(exc.code)
