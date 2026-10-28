# Acceptance model pipeline

Web app to upload images, label them (React UI and/or Label Studio), train a binary classifier on the **host** (Apple **MPS**, NVIDIA **CUDA**, or CPU), export the model, and test on new images.

The parent [`page-classifier`](../) directory keeps the original CLI scripts unchanged. This folder is the **git repository root**.

See [`plan.md`](plan.md) for step-by-step training and testing, and the intended **granular commit** sequence.

## Prerequisites

- Python 3.11+
- Node.js 18+
- [Label Studio](https://labelstud.io/) running locally, e.g. `label-studio start` → http://localhost:8080
- Label Studio **API token** (Account & Settings → Access Token)

## Setup

```bash
cd acceptance-model-pipeline
cp .env.example .env
# Edit .env: LABEL_STUDIO_API_TOKEN, JWT_SECRET, PUBLIC_BASE_URL

cd backend
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt

cd ../frontend
npm install
```

## Run (host)

Terminal 1 — backend:

```bash
cd backend
source .venv/bin/activate
uvicorn app.main:app --reload --port 8000
```

Terminal 2 — frontend:

```bash
cd frontend
npm run dev
```

Open http://localhost:5173

Ensure `PUBLIC_BASE_URL` in `.env` matches how Label Studio reaches images (usually `http://localhost:8000`). Label Studio must be able to fetch `/api/media/...` URLs when displaying tasks.

## Training vs testing (summary)

| Step | Where |
|------|--------|
| Register / login | App UI |
| Create project | App UI (creates Label Studio project) |
| Upload images | App workspace |
| Label | App buttons and/or Label Studio link |
| Train | App **Train model** (uses MPS/CUDA/CPU on host) |
| Export | **Download model** → `.pth` |
| Test | **Test model** page → upload one image |

Original uploads stay in `data/projects/{id}/uploads/`. Training copies into `data/projects/{id}/staging/{run_id}/` only.

## API docs

With backend running: http://localhost:8000/docs
