# CLI workflow (no web UI)

Use this path when you already labeled images in **Label Studio** and exported JSON. The same training approach powers the web app; these scripts are a minimal local alternative.

## What you need

- Python 3.11+ with PyTorch (easiest: reuse the backend venv)

```bash
cd ../backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Steps

```text
Label Studio  →  export.json  →  dataset/  →  model.pth  →  predict
```

| Step | Command |
|------|---------|
| 1. Export | In Label Studio: **Export** → **JSON** → save as `cli/export.json` |
| 2. Prepare | `python cli/prepare_dataset.py` |
| 3. Train | `python cli/train.py` |
| 4. Predict | `python cli/predict.py /path/to/photo.jpg` |

Run commands from the **repository root** (`acceptance-model-pipeline/`), or `cd cli` and use `python prepare_dataset.py` (paths default to the `cli/` folder).

### Class names

Defaults match **blank** / **filled** choices. If your project uses other names:

```bash
python cli/prepare_dataset.py --class-a reject --class-b accept
```

### Options

```bash
python cli/prepare_dataset.py --export ./my-export.json --dataset ./my-dataset
python cli/predict.py photo.jpg --model ./my-model.pth
```

## Rules of thumb

- At least **two labeled images per class** before training.
- `export.json`, `dataset/`, and `model.pth` stay **local** (gitignored).
- If `prepare_dataset.py` cannot find files, check Label Studio’s upload folder under `~/Library/Application Support/label-studio` (macOS) or paths listed in the script.

## Web app instead?

See the [main README](../README.md) for upload, labeling, training, and testing in the browser.
