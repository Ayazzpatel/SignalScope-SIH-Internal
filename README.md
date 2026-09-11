# SignalScope — Telling Real From Synthetic

SIH 2026 Internal Hackathon · Problem Statement 2

SignalScope gives a **likelihood assessment** of whether an image is real or AI-generated, with a heat-map of
the regions behind the verdict and any provenance metadata the image carries. It never makes accusations —
results are presented as *likely real*, *uncertain* or *likely AI-generated*.

> 🚧 Work in progress. Status: **Phase 0 — foundation** (app skeleton + mock detector).

## Quick start

### Option A — Docker (recommended)

```bash
docker compose up --build
```

| URL | What |
|---|---|
| http://localhost:8080 | Web app |
| http://localhost:8000/docs | Interactive API docs |

### Option B — Local development

**Backend** (Python 3.12+)

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate    macOS/Linux: source .venv/bin/activate
pip install -r app/backend/requirements-dev.txt
cd app/backend
cp .env.example .env
uvicorn signalscope.main:app --reload
```

**Frontend** (Node 20+)

```bash
cd app/frontend
npm install
npm run dev          # http://localhost:5173 — proxies /api to :8000
```

**Tests & lint**

```bash
cd app/backend && pytest && ruff check .
cd app/frontend && npm run lint && npm run build
pre-commit install   # once, from repo root
```

## Architecture

```
Browser (React) ──► FastAPI /api/v1 ──► Detector interface
                                          ├── MockDetector  (DETECTOR=mock, default)
                                          └── MLDetector    (DETECTOR=ml → model/predict.py)
```

The application and the ML model are decoupled by a single contract — see
[`docs/ml-contract.md`](docs/ml-contract.md). The app runs end-to-end on a deterministic mock detector until
the real model is plugged in by setting `DETECTOR=ml`.

## Repository layout

```
app/
  backend/            FastAPI service
    signalscope/
      api/            HTTP routes
      core/           settings
      schemas/        request/response models
      services/       detector adapters (mock + ML)
    tests/
  frontend/           React + Vite + Tailwind
model/                ML team — training + predict interface
report/               model report & explanation samples
docs/                 ML contract
```

## Modules

| Module | Status |
|---|---|
| Core: real vs AI-generated classification | 🚧 app ready for model (mock) |
| A. Faithful explanation (heat-map + cues) | 🚧 contract defined |
| B. Generator attribution | 🚧 contract defined |
| C. Robustness to degradation | ⏳ planned |
| D. Provenance & metadata | ⏳ planned |
| F. Deployable interface | 🚧 in progress |

## Datasets, metrics, demo

To be completed — see the model report in `/report`.
