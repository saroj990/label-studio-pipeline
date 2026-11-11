# Frontend (Vite + React)

Web UI for login, project management, image upload and labeling, training progress, model download, and single-image test inference.

## Setup

```bash
cd frontend
npm install
```

## Run

Start the backend on port 8000 first (see [backend README](../backend/README.md)).

```bash
npm run dev
```

Open **http://localhost:5173**. Vite proxies `/api` requests to the backend.

## Scripts

| Command | Description |
|---------|-------------|
| `npm run dev` | Development server |
| `npm run build` | Production build to `dist/` |
| `npm run preview` | Preview production build |

## Pages

- **Login / register** — JWT stored for API calls
- **Projects** — create binary-classifier projects (links to Label Studio)
- **Workspace** — upload, label, train, download `.pth`
- **Test** — upload one image and view class scores

See the [pipeline README](../README.md) for prerequisites and the full checklist.
