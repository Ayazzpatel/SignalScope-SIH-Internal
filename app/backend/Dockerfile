# Build context is the repo root (see docker-compose.yml) so the image can include the `model/` package.
# Model weights are NOT baked in — docker-compose mounts model/model/ at /srv/model/model.
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /srv/app/backend

# CPU-only PyTorch first: the default Linux wheels bundle CUDA and add several GB.
RUN pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu

COPY app/backend/requirements.txt .
RUN pip install -r requirements.txt

COPY app/backend/alembic.ini .
COPY app/backend/signalscope ./signalscope
# Inference modules; the app imports them as `model.*` from the repo root (/srv).
COPY model/*.py /srv/model/

RUN useradd --create-home --uid 1000 signalscope
USER signalscope

EXPOSE 8000
# --proxy-headers: trust X-Forwarded-For from nginx so rate limits and session IPs see the real client.
CMD ["uvicorn", "signalscope.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--forwarded-allow-ips=*"]
