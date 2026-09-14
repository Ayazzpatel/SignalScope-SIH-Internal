# SignalScope — Telling Real From Synthetic

SIH 2026 Internal Hackathon · Problem Statement 2

SignalScope gives a **likelihood assessment** of whether an image is real or AI-generated, with a heat-map of
the regions behind the verdict and any provenance metadata the image carries. It never makes accusations —
results are presented as *likely real*, *uncertain* or *likely AI-generated*.

> 🚧 Work in progress. Status: **Phase 3 — history & privacy** (guest analysis, accounts, private scan history,
> privacy controls). The detector is currently a deterministic mock until the ML model is plugged in.

## Quick start

### Option A — Docker (recommended)

```bash
docker compose up --build
```

| URL | What |
|---|---|
| http://localhost:8080 | Web app |
| http://localhost:8000/docs | Interactive API docs |

Starts Postgres, the API and the web app. Migrations run automatically and demo accounts are seeded:

| Email | Password | Role |
|---|---|---|
| `demo@signalscope.dev` | `SignalScope#2026` | user |
| `reviewer@signalscope.dev` | `SignalScope#2026` | reviewer |
| `admin@signalscope.dev` | `SignalScope#2026` | admin |

> The compose file ships demo defaults (`SECRET_KEY`, DB password, seeded accounts) so it runs with zero setup.
> For any real deployment set `SECRET_KEY`, `POSTGRES_PASSWORD`, `SEED_DEMO_USERS=false` and serve over HTTPS
> with `COOKIE_SECURE=true`.

### Option B — Local development

**Backend** (Python 3.12+). Uses a local SQLite file by default — no database server needed.

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate    macOS/Linux: source .venv/bin/activate
pip install -r app/backend/requirements-dev.txt
cd app/backend
cp .env.example .env
uvicorn signalscope.main:app --reload
```

To develop against Postgres instead:

```bash
docker run -d --name signalscope-pg -p 55432:5432 \
  -e POSTGRES_USER=signalscope -e POSTGRES_PASSWORD=signalscope -e POSTGRES_DB=signalscope postgres:16-alpine
# then in app/backend/.env:
# DATABASE_URL=postgresql+asyncpg://signalscope:signalscope@localhost:55432/signalscope
```

**Frontend** (Node 20+)

```bash
cd app/frontend
npm install
npm run dev          # http://localhost:5173 — proxies /api to :8000
```

**Tests & lint**

```bash
cd app/backend && pytest && ruff check .          # SQLite, one fresh DB per test
TEST_DATABASE_URL=postgresql+asyncpg://signalscope:signalscope@localhost:55432/signalscope pytest   # same suite on Postgres
cd app/frontend && npm run lint && npm run build
pre-commit install   # once, from repo root
```

**Database migrations** (Alembic, run automatically at startup)

```bash
cd app/backend
alembic revision --autogenerate -m "describe change"
alembic upgrade head
```

## Architecture

```
Browser (React) ──► nginx ──► FastAPI /api/v1 ──► Detector interface ── MockDetector | MLDetector (model/predict.py)
                                    │
                                    ├──► PostgreSQL (users, sessions, scans)   ← SQLAlchemy 2 async + Alembic
                                    └──► File storage (heat-maps, opted-in images) on a Docker volume
```

### API

| Endpoint | Purpose |
|---|---|
| `GET /api/v1/health` | Service, detector and database status |
| `POST /api/v1/analyze` | Multipart `file` (JPEG/PNG/WebP, ≤ 20 MB) → verdict band, calibrated `prob_ai`, heat-map overlay, cues, attribution, provenance |
| `POST /api/v1/auth/signup` · `/login` · `/logout` · `/logout-all` | Account lifecycle (sets httpOnly cookies) |
| `POST /api/v1/auth/refresh` | Rotate session tokens |
| `GET /api/v1/auth/session` | Current user or `null` (app bootstrap; refreshes transparently) |
| `GET` / `PATCH /api/v1/auth/me` | Profile |
| `POST /api/v1/auth/change-password` | Change password (signs out other devices) |
| `GET /api/v1/auth/sessions` · `DELETE /api/v1/auth/sessions/{id}` | List / revoke signed-in devices |
| `GET /api/v1/scans` · `/scans/stats` | Your history (cursor pagination; filter by verdict, filename, date) and totals |
| `GET` / `DELETE /api/v1/scans/{id}` · `/scans/{id}/image` · `/heatmap` | One saved scan and its owner-only files |
| `POST /api/v1/scans/bulk-delete` · `DELETE /api/v1/scans` | Delete several / all scans |
| `PATCH /api/v1/account/preferences` · `GET /account/export` · `POST /account/delete` | Privacy settings, data export, account deletion |

```bash
curl -F "file=@photo.jpg" http://localhost:8000/api/v1/analyze
```

Errors always use one envelope: `{"error": {"code", "message", "request_id", "field"?}}`. Every response carries
an `X-Request-ID` header. Uploads are processed in memory and never stored.

### Analysis pipeline

```
upload → validate & decode (real format, size, pixel limit, EXIF orientation)
       → detector (worker thread, concurrency cap, timeout)  ‖  provenance (EXIF, XMP/IPTC, PNG text, C2PA)
       → verdict band (likely real / uncertain / likely AI) + metadata-agreement note
       → heat-map rendered as transparent PNG overlay
```

The application and the ML model are decoupled by a single contract — see
[`docs/ml-contract.md`](docs/ml-contract.md). The app runs end-to-end on a deterministic mock detector until
the real model is plugged in by setting `DETECTOR=ml`.

### Authentication & security

| Concern | Approach |
|---|---|
| Passwords | Argon2id; 10–128 chars, not common, must not contain the email name |
| Access token | 15-minute JWT in an **httpOnly, SameSite=Lax** cookie (or `Authorization: Bearer`) |
| Refresh token | Opaque random token, stored only as a SHA-256 hash; cookie scoped to `/api/v1/auth` |
| Rotation | Every refresh issues a new token; **re-use of a rotated token revokes the whole session** (theft detection), with a short grace window for concurrent tabs |
| Revocation | Session validity is checked on every request, so sign-out / revoke takes effect immediately |
| Brute force | Per-IP rate limits on login/signup; account lock for 15 min after 5 failures |
| Enumeration | Identical response and timing for "unknown email" and "wrong password" |
| CSRF | SameSite cookies + Origin check on state-changing requests |
| Roles | `user` / `reviewer` / `admin` via a `require_role(...)` dependency |

Known limitations: no email verification or password reset yet (needs an SMTP service); rate limiting is
in-memory (single instance — use Redis when scaling out).

### History & privacy

| Concern | Approach |
|---|---|
| Guests | Nothing stored — not the image, not the result, not a hash |
| Signed-in scans | Result (verdict, cues, provenance, heat-map) saved; the **image only on opt-in** (off by default) |
| Stored images | Re-encoded to WebP ≤ 1024 px, which drops all metadata including GPS; served only to the owner |
| Seen before | SHA-256 (exact) + 64-bit perceptual hash (survives resize/re-compression, Hamming ≤ 8) |
| Other users | Only an anonymous count, and only when ≥ 2 other people scanned it |
| Result cache | Identical file + same model version reuses the stored result (no re-inference) |
| Retention | Per user: 7 / 30 / 90 (default) / 365 days or forever; hourly clean-up job |
| Your rights | Export everything as JSON; delete one, many or all scans; delete the account (password-confirmed) |
| Access control | Other users' scans return 404 (existence is never confirmed) |

## Repository layout

```
app/
  backend/            FastAPI service
    signalscope/
      api/            HTTP routes
      core/           settings, security, errors, middleware
      db/             engine, base types, migration runner
      migrations/     Alembic revisions
      models/         SQLAlchemy tables
      schemas/        request/response models
      services/       analysis, provenance, auth, detector adapters (mock + ML)
    tests/
  frontend/           React + Vite + Tailwind
model/                ML team — training + predict interface
report/               model report & explanation samples
docs/                 ML contract
```

## Modules

| Module | Status |
|---|---|
| Core: real vs AI-generated classification | 🚧 end-to-end flow done; awaiting real model |
| A. Faithful explanation (heat-map + cues) | 🚧 UI done (overlay, regions, cue list); awaiting model output |
| B. Generator attribution | 🚧 UI done; awaiting model output |
| C. Robustness to degradation | ⏳ planned |
| D. Provenance & metadata | ✅ EXIF, IPTC/XMP, generator text chunks, C2PA Content Credentials |
| F. Deployable interface | 🚧 drag-drop / paste upload, responsible verdict UI, accounts |

## Datasets, metrics, demo

To be completed — see the model report in `/report`.
