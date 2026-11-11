"""Build an ImageFolder dataset from a Label Studio JSON export."""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path
from urllib.parse import unquote, urlparse

SCRIPT_DIR = Path(__file__).resolve().parent

# Common Label Studio media locations when exports reference upload URLs.
SEARCH_ROOTS = [
    Path.home() / ".local/share/label-studio",
    Path.home() / "Library/Application Support/label-studio",
    Path.home() / "label-studio-data",
]


def normalize(value: str) -> str:
    return str(value).strip().lower().replace("_", "-")


def find_image(image_ref: str) -> Path:
    parsed = urlparse(str(image_ref))
    path = unquote(parsed.path)
    filename = Path(path).name

    direct = Path(path)
    if direct.is_file():
        return direct

    for root in SEARCH_ROOTS:
        if not root.exists():
            continue
        matches = list(root.rglob(filename))
        if matches:
            return matches[0]

    raise FileNotFoundError(
        f"Cannot find {filename} on disk. Image reference: {image_ref}"
    )


def get_label(task: dict, class_a: str, class_b: str) -> str | None:
    allowed = {
        normalize(class_a): class_a,
        normalize(class_b): class_b,
    }

    for annotation in reversed(task.get("annotations", [])):
        if annotation.get("was_cancelled"):
            continue
        for result in annotation.get("result", []):
            choices = result.get("value", {}).get("choices", [])
            for choice in choices:
                key = normalize(str(choice))
                if key in allowed:
                    return allowed[key]
                for norm, original in allowed.items():
                    if norm in key or key in norm:
                        return original
    return None


def folder_for_label(label: str) -> str:
    return normalize(label).replace(" ", "-")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--export",
        type=Path,
        default=SCRIPT_DIR / "export.json",
        help="Label Studio JSON export (default: cli/export.json)",
    )
    parser.add_argument(
        "--dataset",
        type=Path,
        default=SCRIPT_DIR / "dataset",
        help="Output ImageFolder root (default: cli/dataset)",
    )
    parser.add_argument("--class-a", default="blank", help="First class name in LS")
    parser.add_argument("--class-b", default="filled", help="Second class name in LS")
    args = parser.parse_args()

    if not args.export.is_file():
        raise SystemExit(f"Export file not found: {args.export}")

    tasks = json.loads(args.export.read_text())
    if not isinstance(tasks, list):
        raise SystemExit("Expected a JSON list (Label Studio export format).")

    for label in (args.class_a, args.class_b):
        (args.dataset / folder_for_label(label)).mkdir(parents=True, exist_ok=True)

    copied = {args.class_a: 0, args.class_b: 0}
    skipped = 0

    for task in tasks:
        label = get_label(task, args.class_a, args.class_b)
        if label is None:
            skipped += 1
            continue

        data = task.get("data", {})
        image_ref = data.get("image") or data.get("image_url")
        if not image_ref:
            print(f"Skipping task {task.get('id')}: no image field")
            skipped += 1
            continue

        source = find_image(str(image_ref))
        dest_dir = args.dataset / folder_for_label(label)
        destination = dest_dir / f"task_{task.get('id')}_{source.name}"
        shutil.copy2(source, destination)
        copied[label] += 1
        print(f"{label:12} <- {source.name}")

    print("\nDataset preparation complete.")
    for name, count in copied.items():
        print(f"  {name}: {count}")
    print(f"  Skipped: {skipped}")

    if not all(copied.values()):
        raise SystemExit(
            "Each class needs at least one labeled image. "
            "Check class names match Label Studio choices."
        )


if __name__ == "__main__":
    main()
