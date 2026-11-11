# Page classifier (acceptance model pipeline)

Train a **two-class image classifier**—for example blank vs filled pages—from photos. Two ways to work:

| Path | Best when |
|------|-----------|
| **[Web app](#web-app)** | You want upload, labeling, training, and testing in the browser |
| **[CLI](cli/README.md)** | You already have a Label Studio JSON export and prefer three Python commands |

Both use **MobileNet V3 Small** (PyTorch) on your machine: Apple **MPS**, NVIDIA **CUDA**, or **CPU**.

---

## Web app

### What runs where

```text
Browser (localhost:5173)  →  FastAPI (localhost:8000)  →  Label Studio (localhost:8080)
                              train / predict on GPU or CPU
```

### Prerequisites

- Python 3.11+, Node.js 18+
- [Label Studio](https://labelstud.io/) for project sync (e.g. `label-studio start` → http://localhost:8080)
- Label Studio **API token** in `.env` (Account → Legacy Token or Personal Access Token). This is **not** the same as your app login JWT.

### First-time setup

```bash
cp .env.example .env
# Set LABEL_STUDIO_API_TOKEN, JWT_SECRET, PUBLIC_BASE_URL=http://localhost:8000

cd backend && python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

cd ../frontend && npm install
```

### Start

```bash
# Terminal 1 — optional but required to create projects
label-studio start

# Terminal 2
cd backend && source .venv/bin/activate
uvicorn app.main:app --reload --port 8000

# Terminal 3
cd frontend && npm run dev
```

Open **http://localhost:5173**. API docs: **http://localhost:8000/docs**.

Label Studio must reach uploaded images via `PUBLIC_BASE_URL` (usually `http://localhost:8000/api/media/...`).

### Workflow in the UI

1. **Register / log in**
2. **Create project** — pick two class names (e.g. blank, filled)
3. **Upload** images in the workspace
4. **Label** each image (in-app or via the Label Studio link)
5. **Train model** — needs ≥2 images per class; progress shows in the UI
6. **Download** `.pth` or use **Test** with a new photo

Training copies images into `data/projects/{id}/staging/`; originals stay in `uploads/`. Project data is gitignored.

More detail: [backend/README.md](backend/README.md), [frontend/README.md](frontend/README.md).

---

## CLI

Label in Label Studio → export JSON → prepare → train → predict.

Full instructions: **[cli/README.md](cli/README.md)**.

```bash
# From repo root, with backend venv active:
python cli/prepare_dataset.py   # expects cli/export.json
python cli/train.py             # writes cli/model.pth
python cli/predict.py path/to/image.jpg
```

---

## Repository layout

```text
acceptance-model-pipeline/
├── README.md          ← you are here
├── cli/               ← Label Studio export workflow
├── backend/           ← FastAPI + training services
├── frontend/          ← React UI
├── .env.example       ← copy to .env (never commit .env)
└── data/              ← created at runtime (gitignored)
```

Implementation notes for contributors: [plan.md](plan.md).
