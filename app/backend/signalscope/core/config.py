import secrets
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# app/backend/signalscope/core/config.py -> repo root is 4 levels up
REPO_ROOT = Path(__file__).resolve().parents[4]
BACKEND_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "SignalScope"
    environment: Literal["development", "test", "production"] = "development"
    api_prefix: str = "/api/v1"
    cors_origins: list[str] = ["http://localhost:5173"]

    # Detector selection — see docs/ml-contract.md
    detector: Literal["mock", "ml"] = "ml"
    mock_latency_ms: int = 0
    ml_module: str = "model.predict"
    ml_root: Path = REPO_ROOT
    ml_device: str = "cpu"
    signalscope_model_path: str = ""

    # Verdict bands applied to the calibrated prob_ai
    band_likely_real_max: float = 0.35
    band_likely_ai_min: float = 0.65

    # Combined verdict (/analyze/ensemble): "likely AI" if ANY model's P(AI) reaches this value
    ensemble_ai_threshold: float = 0.25

    # Upload limits
    max_upload_mb: int = 20
    max_image_pixels: int = 40_000_000  # ~40 MP; guards against decompression bombs

    # Inference
    inference_timeout_s: float = 30.0
    max_concurrent_inference: int = 2
    heatmap_max_side: int = 1024

    # Database — Postgres in Docker; SQLite fallback for quick local runs without Docker
    database_url: str = f"sqlite+aiosqlite:///{(BACKEND_ROOT / 'data' / 'signalscope.db').as_posix()}"
    auto_migrate: bool = True
    seed_demo_users: bool = False

    # Auth
    secret_key: str = ""  # required in production; generated per-process in development
    access_token_ttl_s: int = 15 * 60
    refresh_ttl_remember_s: int = 30 * 24 * 3600
    refresh_ttl_default_s: int = 24 * 3600
    refresh_reuse_grace_s: int = 30  # concurrent-tab refresh race window
    cookie_secure: bool | None = None  # default: True in production
    max_failed_logins: int = 5
    lockout_minutes: int = 15
    login_rate_per_minute: int = 10
    signup_rate_per_minute: int = 5
    argon2_time_cost: int = 3
    argon2_memory_kib: int = 64 * 1024

    @property
    def max_upload_bytes(self) -> int:
        return self.max_upload_mb * 1024 * 1024

    @property
    def secure_cookies(self) -> bool:
        return self.cookie_secure if self.cookie_secure is not None else self.environment == "production"

    @model_validator(mode="after")
    def _validate(self) -> "Settings":
        if not 0 <= self.band_likely_real_max < self.band_likely_ai_min <= 1:
            raise ValueError("Require 0 <= BAND_LIKELY_REAL_MAX < BAND_LIKELY_AI_MIN <= 1")
        if not 0 < self.ensemble_ai_threshold <= 1:
            raise ValueError("Require 0 < ENSEMBLE_AI_THRESHOLD <= 1")
        if not self.secret_key:
            if self.environment == "production":
                raise ValueError("SECRET_KEY must be set in production")
            # Dev convenience: sessions reset when the server restarts.
            self.secret_key = secrets.token_urlsafe(48)
        elif len(self.secret_key) < 32:
            raise ValueError("SECRET_KEY must be at least 32 characters")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
