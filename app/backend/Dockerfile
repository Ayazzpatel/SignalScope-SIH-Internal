FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /srv/app/backend

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY alembic.ini .
COPY signalscope ./signalscope

RUN useradd --create-home --uid 1000 signalscope
USER signalscope

EXPOSE 8000
# --proxy-headers: trust X-Forwarded-For from nginx so rate limits and session IPs see the real client.
CMD ["uvicorn", "signalscope.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--forwarded-allow-ips=*"]
