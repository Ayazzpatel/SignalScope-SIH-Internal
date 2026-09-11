from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# app/backend/signalscope/core/config.py -> repo root is 4 levels up
REPO_ROOT = Path(__file__).resolve().parents[4]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "SignalScope"
    environment: Literal["development", "test", "production"] = "development"
    api_prefix: str = "/api/v1"
    cors_origins: list[str] = ["http://localhost:5173"]

    # Detector selection — see docs/ml-contract.md
    detector: Literal["mock", "ml"] = "mock"
    mock_latency_ms: int = 0
    ml_module: str = "model.predict"
    ml_root: Path = REPO_ROOT
    ml_device: str = "cpu"

    # Verdict bands applied to the calibrated prob_ai
    band_likely_real_max: float = 0.35
    band_likely_ai_min: float = 0.65

    @model_validator(mode="after")
    def _check_bands(self) -> "Settings":
        if not 0 <= self.band_likely_real_max < self.band_likely_ai_min <= 1:
            raise ValueError("Require 0 <= BAND_LIKELY_REAL_MAX < BAND_LIKELY_AI_MIN <= 1")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
