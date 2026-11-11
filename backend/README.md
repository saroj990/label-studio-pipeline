# Backend (FastAPI)

REST API for projects, Label Studio integration, image upload, training (PyTorch MobileNet V3 on host MPS/CUDA/CPU), model export, and inference.

## Setup

From the pipeline root, copy `.env.example` to `.env` and set `JWT_SECRET`, `LABEL_STUDIO_URL`, `LABEL_STUDIO_API_TOKEN`, and `PUBLIC_BASE_URL`.

```bash
cd backend
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Run

```bash
source .venv/bin/activate
uvicorn app.main:app --reload --port 8000
```

- Health: `GET http://localhost:8000/health`
- OpenAPI: `http://localhost:8000/docs`

Label Studio must be running separately when you create projects or sync labels (`label-studio start`).

## Layout

| Path | Purpose |
|------|---------|
| `app/main.py` | FastAPI app and router wiring |
| `app/routers/` | Auth, projects, media |
| `app/services/` | Label Studio client, dataset build, training, predict |
| `app/auth/` | JWT and password hashing |

Project data (uploads, staging datasets, models) lives under `data/` at the pipeline root (gitignored).

See the [main README](../README.md) for the web workflow, or [cli/README.md](../cli/README.md) for export-only training.
