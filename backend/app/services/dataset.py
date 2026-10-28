from __future__ import annotations

import shutil
from pathlib import Path
from urllib.parse import unquote, urlparse


def normalize_choice(value: str) -> str:
    return str(value).strip().lower().replace("_", "-")


def parse_label(task: dict, class_names: tuple[str, str]) -> str | None:
    allowed = {normalize_choice(c): c for c in class_names}

    for annotation in reversed(task.get("annotations", [])):
        if annotation.get("was_cancelled"):
            continue
        for result in annotation.get("result", []):
            choices = result.get("value", {}).get("choices", [])
            for choice in choices:
                key = normalize_choice(str(choice))
                if key in allowed:
                    return allowed[key]
                for norm, original in allowed.items():
                    if norm in key or key in norm:
                        return original
    return None


def image_filename_from_task(task: dict) -> str | None:
    data = task.get("data") or {}
    image_ref = data.get("image") or data.get("image_url")
    if not image_ref:
        meta = task.get("meta") or {}
        image_ref = meta.get("filename")
    if not image_ref:
        return None
    parsed = urlparse(str(image_ref))
    path = unquote(parsed.path)
    return Path(path).name


def resolve_upload_path(uploads_dir: Path, task: dict) -> Path | None:
    filename = image_filename_from_task(task)
    if not filename:
        return None
    direct = uploads_dir / filename
    if direct.is_file():
        return direct
    task_id = task.get("id")
    if task_id is not None:
        matches = list(uploads_dir.glob(f"task_{task_id}_*"))
        if matches:
            return matches[0]
    return None


def build_dataset_from_export(
    tasks: list[dict],
    uploads_dir: Path,
    dataset_dir: Path,
    class_names: tuple[str, str],
) -> dict[str, int]:
    for name in class_names:
        (dataset_dir / name).mkdir(parents=True, exist_ok=True)

    copied = {class_names[0]: 0, class_names[1]: 0}
    skipped = 0

    for task in tasks:
        label = parse_label(task, class_names)
        if label is None:
            skipped += 1
            continue
        source = resolve_upload_path(uploads_dir, task)
        if source is None:
            skipped += 1
            continue
        dest = dataset_dir / label / f"task_{task.get('id')}_{source.name}"
        shutil.copy2(source, dest)
        copied[label] += 1

    copied["_skipped"] = skipped
    return copied
