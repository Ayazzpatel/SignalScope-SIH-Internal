from collections.abc import Iterator

import numpy as np
import pytest
from fastapi.testclient import TestClient
from PIL import Image

from signalscope.core.config import get_settings
from signalscope.main import create_app


@pytest.fixture(autouse=True)
def _test_settings(monkeypatch) -> Iterator[None]:
    """Isolate tests from a developer's local .env."""
    monkeypatch.setenv("ENVIRONMENT", "test")
    monkeypatch.setenv("DETECTOR", "mock")
    monkeypatch.setenv("MOCK_LATENCY_MS", "0")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture
def client() -> Iterator[TestClient]:
    with TestClient(create_app()) as test_client:  # context manager runs lifespan
        yield test_client


@pytest.fixture
def image() -> Image.Image:
    rng = np.random.default_rng(0)
    return Image.fromarray(rng.integers(0, 256, size=(96, 128, 3), dtype=np.uint8))
