# SignalScope — Telling Real From Synthetic

SIH 2026 Internal Hackathon · Problem Statement 2 · L. J. Institute of Engineering and Technology

SignalScope gives a **likelihood assessment** of whether an image is real or AI-generated. Three independently
trained detectors look at every upload, and the user sees one clear, responsibly worded result —
**Likely AI-generated** or **Likely real** — next to the provenance metadata the file carries (C2PA, IPTC/XMP,
EXIF). It never makes accusations, and it is scoped to general imagery (scenes, objects, art, products) — not
face-swaps of real people or claims about real events.

---

## 1. Get the code

All current work lives on the **`development_sujal`** branch. Clone that branch:

```bash
git clone -b development_sujal https://github.com/Ayazzpatel/SignalScope-SIH-Internal.git
cd SignalScope-SIH-Internal
```

Already cloned? Switch to it with `git fetch origin && git checkout development_sujal`.

### Model weights (required, not in git)

Checkpoints are ~330 MB each and are gitignored. Place them exactly here (download link: _TODO — add release link_):

| Model | File |
|---|---|
| E1 | `model/model/signalscope_E1/E1_convnext_tiny_best.pt` |
| Standalone-M | `model/model/Standalone_M/best_model.pt` |
| E2 | `model/model/signalscope_E2_modern/last_model.pt` |

The app finds them automatically. A different location can be set with `SIGNALSCOPE_MODEL_PATH`,
`SIGNALSCOPE_STANDALONE_MODEL_PATH` and `SIGNALSCOPE_E2_MODEL_PATH`. If a secondary model's weights are missing,
the app still runs and the result card reads "Checked by 2 of 3 detection models"; E1 is required.

---

## 2. Modules built

| Module | Status | What exists |
|---|---|---|
| **Core** — real vs AI classification | ✅ | 3 ConvNeXt-Tiny detectors (E1, Standalone-M, E2) combined into one verdict; label + score via API |
| A. Faithful explanation | 🚧 | UI ready (heat-map overlay, region highlights, cue list); the models do not produce heat-maps/cues yet |
| B. Generator attribution | 🚧 | UI + API field ready; no attribution model yet |
| C. Robustness to degradation | 🚧 | Training augments with JPEG (q40–100), blur, resize/crop, colour jitter; no degradation-vs-accuracy study yet |
| D. Provenance & metadata | ✅ | C2PA Content Credentials, IPTC/XMP digital-source-type, generator text chunks, EXIF; agreement with the visual verdict is explained |
| E. Multimodal (image + text) | ❌ | Not attempted |
| F. Real-time / deployable | ✅ | Drag-and-drop, paste and **batch scan**, minimal verdict UI, accounts, Docker one-command start, ~0.5 s per image on CPU |
| G. Active defence analysis | ❌ | Not attempted |

---

## 3. Run it

### Option A — Docker (recommended)

Needs Docker Desktop and the weights from §1.

```bash
docker compose up --build
```

| URL | What |
|---|---|
| http://localhost:8080 | Web app |
| http://localhost:8000/docs | Interactive API docs |

Starts Postgres, the API (with all three models, CPU) and the web app. The backend takes up to ~90 s to become
healthy while models load. Migrations run automatically and demo accounts are seeded:

| Email | Password | Role |
|---|---|---|
| `demo@signalscope.dev` | `SignalScope#2026` | user |
| `reviewer@signalscope.dev` | `SignalScope#2026` | reviewer |
| `admin@signalscope.dev` | `SignalScope#2026` | admin |

Accounts are optional — guests can scan images. Run without models (UI only) with `DETECTOR=mock docker compose up --build`.

> The compose file ships demo defaults (`SECRET_KEY`, DB password, seeded accounts) so it runs with zero setup.
> For any real deployment set `SECRET_KEY`, `POSTGRES_PASSWORD`, `SEED_DEMO_USERS=false` and serve over HTTPS
> with `COOKIE_SECURE=true`.

### Option B — Local development

**Backend** (Python 3.12+). Uses a local SQLite file by default — no database server needed.

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate    macOS/Linux: source .venv/bin/activate
pip install -r app/backend/requirements-dev.txt   # includes torch, torchvision, timm, opencv
cd app/backend
cp .env.example .env                              # DETECTOR=ml by default
uvicorn signalscope.main:app --reload             # http://localhost:8000/docs
```

For a smaller CPU-only PyTorch install, run
`pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu` first.

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

### Reproduce a prediction in under a minute

With the backend running (either option):

```bash
curl -F "file=@photo.jpg" http://localhost:8000/api/v1/analyze/ensemble
```

`final.headline` is the verdict shown to users; `models[]` lists each model's `ai_probability`.
Without a server, from the repo root, the E1 predict interface alone:

```bash
python -c "from PIL import Image; from model.predict import load_model, predict; m = load_model('cpu'); print(predict(m, Image.open('photo.jpg'))['ai_probability'])"
```

### Tests & lint

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

---

## 4. How a verdict is made

```
upload → validate & decode (real format, size, pixel limit, EXIF orientation)
       → E1 ‖ Standalone-M ‖ E2 (worker threads, concurrency cap, timeout)  ‖  provenance (EXIF, XMP/IPTC, PNG text, C2PA)
       → combined verdict: "Likely AI-generated" if AT LEAST 2 of the 3 models give P(AI) ≤ 0.25, else "Likely real"
         (reversed vote, ENSEMBLE_INVERT=true — see Known limitations; false = "≥ threshold")
       → metadata-agreement note (does declared provenance agree with the verdict?)
```

- **Why 2 of 3 models?** The three models were trained on different data and fail on different images.
  Requiring two of them to agree stops a single model from deciding on its own. If a model is unavailable, all
  remaining models must agree. Tune it with `ENSEMBLE_MIN_VOTES`, `ENSEMBLE_AI_THRESHOLD` and `ENSEMBLE_INVERT`.
- **Minimal, non-accusatory UI.** Users see one verdict, a one-line explanation and "Checked by 3 detection
  models" — no per-model breakdown and no percentage, to avoid false precision.
- A model that fails is reported in the API response and left out of the decision; E1 is required.

The application and the models are decoupled by a small contract — see [`docs/ml-contract.md`](docs/ml-contract.md)
(§7 covers the secondary models and the combined verdict).

---

## 5. Models, datasets and metrics

All three are **ConvNeXt-Tiny** (ImageNet-pretrained, transfer learning) binary classifiers with a single logit
(`0 = real`, `1 = AI`), 224 px input, `BCEWithLogitsLoss`, AdamW.

| Model | Backbone / code | Training data | Held-out evaluation |
|---|---|---|---|
| **E1** | torchvision · `app/backend/signalscope/ML/scripts/genimage.ipynb`, `genimage2.ipynb` | GenImage subsets ADM, BigGAN, GLIDE, SD v1.4, SD v1.5 (≈50k images, balanced, 80/20 train/val) | **Unseen generator: Wukong** (10,007 images, never trained on) |
| **Standalone-M** | timm · `app/backend/signalscope/ML/Local_Training/` | GenImage manifests (see that README), 8 epochs, lr 2e-4 | **Unseen generator: Wukong** (10,007 images) |
| **E2** | torchvision · retrained E1 architecture | 51,752 images: GenImage ADM, BigGAN, GLIDE, SD v1.4, SD v1.5, **Wukong** + Defactify | Random test split (6,899 images) — **not** an unseen-generator test |

| Model | Split | ROC-AUC | Macro-F1 | Accuracy | FPR @ 0.5 | Confusion matrix (TN / FP / FN / TP) |
|---|---|---|---|---|---|---|
| E1 | Normal val (seen generators) | 0.968 | 0.930 | — | — | _TODO_ |
| E1 | **Unseen Wukong** | **0.993** ¹ | 0.960 | — | — | _TODO_ |
| Standalone-M | Normal val | 0.968 | — | — | — | — |
| Standalone-M | **Unseen Wukong** | **0.904** | 0.801 | 0.804 | 0.076 | 4628 / 379 / 1580 / 3420 |
| E2 | Test (mixed, seen generators) | 0.992 | 0.961 | 0.961 | — | _TODO_ |
| Combined verdict | Organizers' held-out set | _TODO_ | _TODO_ | _TODO_ | _TODO_ | _TODO_ |

¹ E1's checkpoint was selected on the Wukong score, so this number is optimistic; Standalone-M (selected on
validation AUC) is the cleaner unseen-generator estimate.

Sources: E1 `model/model/signalscope_E1/E1_history.csv`, Standalone-M `model/model/Standalone_M/metrics.json`
(+ `confusion_matrix_test.png`), E2 `model/model/signalscope_E2_modern/E2_history.csv`.

**Datasets**

| Dataset | Used by | Source | Licence |
|---|---|---|---|
| GenImage (Zhu et al., NeurIPS 2023) — ADM, BigGAN, GLIDE, SD v1.4/v1.5, Wukong subsets | all models | https://github.com/GenImage-Dataset/GenImage (Kaggle mirrors by `vtphatt2`) | _TODO — confirm_ |
| Defactify Image Dataset | E2 | https://huggingface.co/datasets/Rajarshi-Roy-research/Defactify_Image_Dataset | _TODO — confirm_ |
| Organizer-provided dataset (CIFAKE-style) | — | Released at kickoff | _TODO — not used in training yet_ |

---

## 6. Architecture

```
Browser (React) ──► nginx ──► FastAPI /api/v1 ──► E1 (MLDetector, model/predict.py)
                                    │          ├─► Standalone-M (model/predict_standalone.py)
                                    │          └─► E2 (model/predict_e2.py)
                                    │
                                    └──► PostgreSQL (users, sessions)   ← SQLAlchemy 2 async + Alembic
```

### API

| Endpoint | Purpose |
|---|---|
| `GET /api/v1/health` | Service, detector and database status |
| `POST /api/v1/analyze/ensemble` | Multipart `file` (JPEG/PNG/WebP, ≤ 20 MB) → combined `final` verdict, per-model `models[]`, and E1's full `analysis` (evidence, provenance, image info). **Used by the web UI.** |
| `POST /api/v1/analyze` | Same upload → E1 only: verdict band, `prob_ai`, heat-map overlay, cues, attribution, provenance |
| `POST /api/v1/auth/signup` · `/login` · `/logout` · `/logout-all` | Account lifecycle (sets httpOnly cookies) |
| `POST /api/v1/auth/refresh` | Rotate session tokens |
| `GET /api/v1/auth/session` | Current user or `null` (app bootstrap; refreshes transparently) |
| `GET` / `PATCH /api/v1/auth/me` | Profile |
| `POST /api/v1/auth/change-password` | Change password (signs out other devices) |
| `GET /api/v1/auth/sessions` · `DELETE /api/v1/auth/sessions/{id}` | List / revoke signed-in devices |

Errors always use one envelope: `{"error": {"code", "message", "request_id", "field"?}}`. Every response carries
an `X-Request-ID` header. Uploads are processed in memory and never stored.

### Robustness & calibration

- **Robustness:** training augmentation with random JPEG re-compression (quality 40–100), Gaussian blur,
  resized crops, flips and colour jitter; three models with different training data reduce single-model blind spots.
- **Calibration:** model outputs are raw sigmoid probabilities (no temperature scaling yet). The UI therefore
  shows a two-way verdict rather than a percentage.

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

### Known limitations

- **The app's verdict is currently reversed** (`ENSEMBLE_INVERT=true`): an image is called "Likely AI-generated"
  when two models give it a *low* AI probability. The team chose this after the models' verdicts looked reversed
  on their own test images. It contradicts the models' held-out results — e.g. Standalone-M averages P(AI) 0.65
  on unseen AI images vs 0.13 on real ones — so on images like the training/test data the app's verdict will
  mostly be wrong. The predict interfaces in `model/` are **not** reversed. Set `ENSEMBLE_INVERT=false` (with
  `ENSEMBLE_AI_THRESHOLD=0.35`) to restore the normal rule. The combined verdict's FPR and recall have not been
  measured in either mode.
- All three models learned only 2022-era generators (ADM, BigGAN, GLIDE, SD v1.x, Wukong); images from newer
  tools (e.g. Midjourney v6, DALL·E 3, Flux) can be scored as real.
- In every training set, all real images are JPEG and all AI images are PNG, so the models may have learned file
  format as a shortcut. Re-encoding a couple of test images did not change their scores, but this has not been
  ruled out; format-balanced training data would remove the risk.
- E2 was trained on Wukong, so Wukong is no longer an unseen generator for the combined system; a new held-out
  generator (e.g. Midjourney, VQDM) is needed for an honest unseen-split score.
- No heat-maps, cues or generator attribution from the models yet (Modules A/B).
- Probabilities are not calibrated; heavy compression, screenshots, filters and very new generators reduce accuracy.
- No email verification or password reset (needs SMTP); rate limiting is in-memory (single instance).

---

## 7. Repository layout

```
app/
  backend/                FastAPI service
    signalscope/
      api/                HTTP routes
      core/               settings, security, errors, middleware
      db/                 engine, base types, migration runner
      migrations/         Alembic revisions
      models/             SQLAlchemy tables
      schemas/            request/response models
      services/           analysis + ensemble, secondary models, verdict, provenance, auth, detectors
      ML/                 training notebooks (E1/E2), Local_Training package (Standalone-M), manifests
    tests/
  frontend/               React + Vite + Tailwind
model/                    predict interfaces: predict.py (E1), predict_standalone.py, predict_e2.py
  model/                  model weights (gitignored — see §1) and training histories
docs/                     ML ↔ app contract
docker-compose.yml        one-command start (Postgres + API + web)
```

---

## 8. Troubleshooting

| Symptom | Fix |
|---|---|
| `Can't locate revision identified by '...'` on Docker start | The Docker database was migrated by another branch. Reset it with `docker compose down -v` (deletes Docker accounts/history), then `docker compose up --build`. |
| `Checkpoint '...' not found` | Weights are missing — place them as in §1 or set the matching `SIGNALSCOPE_*_MODEL_PATH`. |
| Result says "Checked by 2 of 3 detection models" | A secondary model failed to load; the backend log names it and the reason. |
| Banner says results are a demo | The backend is running with `DETECTOR=mock`. |

---

## 9. Demo

- Demo video: _TODO — add link_
- Deployed app: _TODO — add link (if any)_

## 10. Originality declaration & credits

Built during the hackathon window by the SignalScope team. Third-party components: ImageNet-pretrained
ConvNeXt-Tiny weights via [torchvision](https://pytorch.org/vision/) and [timm](https://github.com/huggingface/pytorch-image-models),
the GenImage and Defactify datasets (§5), and [c2pa-python](https://github.com/contentauth/c2pa-python) for
Content Credentials. No public real-vs-fake notebook was copied. AI coding assistants were used during
development, as permitted by the rules.

## 11. Submission checklist (still open)

- [ ] `/report` — one-page model report (task, data & split, model, metrics, baseline, limitations)
- [ ] Weights release link (§1)
- [ ] Confusion matrices for E1 and E2; combined-verdict AUC / F1 / FPR on the organizers' held-out set
- [ ] Dataset licences confirmed (§5)
- [ ] Demo video link (§9)
