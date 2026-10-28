# Acceptance model pipeline — implementation plan

Host-only setup (no Docker). Training uses PyTorch on the host: **MPS** on Apple Silicon when available, else **CUDA**, else **CPU**.

Label Studio runs separately on the host; the backend talks to it via API (`LABEL_STUDIO_URL`, `LABEL_STUDIO_API_TOKEN`).

Parent folder [`../`](../) (CLI scripts `train.py`, `prepare_dataset.py`, etc.) stays unchanged. All application code lives in this directory; **git root is here**.

---

## Prerequisites

1. Python 3.11+ with venv (can reuse parent `.venv` or create `backend/.venv`).
2. Node.js 18+ for the React frontend.
3. Label Studio installed and running, e.g. `label-studio start` → `http://localhost:8080`.
4. Create a **Legacy Token** or access token in Label Studio account settings.

---

## Step 0 — Environment

| Action | Command / file |
|--------|----------------|
| Copy env template | `cp .env.example .env` and fill values |
| Backend deps | `cd backend && pip install -r requirements.txt` |
| Frontend deps | `cd frontend && npm install` |

**Git commit:** `chore: add pipeline scaffold, plan, and gitignore`

---

## Step 1 — Backend foundation

| Action | Detail |
|--------|--------|
| Start API | `cd backend && uvicorn app.main:app --reload --port 8000` |
| Health | `GET http://localhost:8000/health` |

**Git commit:** `feat(backend): add FastAPI app, config, and SQLite database`

---

## Step 2 — Authentication

| Action | Detail |
|--------|--------|
| Register | `POST /auth/register` `{ "email", "password" }` |
| Login | `POST /auth/login` → JWT |
| Use token | `Authorization: Bearer <token>` on protected routes |

**Git commit:** `feat(backend): add JWT auth and user registration`

---

## Step 3 — Projects and Label Studio

| Action | Detail |
|--------|--------|
| Create project | `POST /projects` `{ "name", "class_a", "class_b" }` — creates linked LS project |
| List projects | `GET /projects` |
| Open LS UI | `GET /projects/{id}/label-studio-url` |

**Git commit:** `feat(backend): integrate Label Studio project creation`

---

## Step 4 — Upload and media

| Action | Detail |
|--------|--------|
| Upload images | `POST /projects/{id}/upload` multipart `files` |
| Serve images | `GET /api/media/{project_id}/{filename}` (for Label Studio task URLs) |
| List tasks | `GET /projects/{id}/tasks` |

**Git commit:** `feat(backend): add image upload, media serving, and task import`

---

## Step 5 — Labeling

| Action | Detail |
|--------|--------|
| Label in app | `POST /projects/{id}/tasks/{task_id}/label` `{ "choice": "<class_a or class_b>" }` |
| Label in LS | Use link from step 3; refresh tasks in app |

**Git commit:** `feat(backend): add annotation API for custom labeling UI`

---

## Step 6 — Training

| Action | Detail |
|--------|--------|
| Requirements | ≥2 labeled images per class |
| Train | `POST /projects/{id}/train` — exports LS JSON, copies images to staging dataset, trains MobileNet V3 small |
| Download | `GET /projects/{id}/models/latest` |

Original uploads under `data/projects/{id}/uploads/` are not modified; only copies are used for training.

**Git commit:** `feat(backend): add dataset build and model training on host GPU/CPU`

---

## Step 7 — Testing (inference)

| Action | Detail |
|--------|--------|
| Predict | `POST /projects/{id}/predict` multipart `file` |
| Response | `{ "prediction", "scores": { "<class>": 0.xx } }` |

**Git commit:** `feat(backend): add predict endpoint for model testing`

---

## Step 8 — Frontend

| Action | Detail |
|--------|--------|
| Dev server | `cd frontend && npm run dev` → proxies `/api` to `:8000` |
| Flow | Login → Projects → Workspace (upload, label, train, download) → Test page |

**Git commits:**

- `feat(frontend): scaffold Vite React app with API client`
- `feat(frontend): add auth, projects, workspace, and test pages`

---

## Step 9 — Documentation and rules

| Action | Detail |
|--------|--------|
| README | Full runbook in [`README.md`](README.md) |
| Cursor rule | [`.cursor/rules/pipeline-scope.mdc`](.cursor/rules/pipeline-scope.mdc) — code only in this folder |

**Git commit:** `docs: add README and Cursor rule for pipeline scope`

---

## End-to-end training checklist

- [ ] Label Studio running; token in `.env`
- [ ] Backend on `:8000`, frontend on `:5173`
- [ ] Register / login
- [ ] Create project with two class names
- [ ] Upload at least 2 images per class
- [ ] Label each image (app or LS)
- [ ] Train → download `.pth`

## End-to-end testing checklist

- [ ] After successful train, open **Test** for that project
- [ ] Upload a new image
- [ ] Confirm prediction and scores match expected class names
