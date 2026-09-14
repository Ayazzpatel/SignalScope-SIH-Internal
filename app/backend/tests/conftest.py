"""Test fixtures.

By default every test gets a fresh SQLite database. To run the whole suite against Postgres:

    TEST_DATABASE_URL=postgresql+asyncpg://signalscope:signalscope@localhost:55432/signalscope pytest

(the Postgres schema is wiped before each test — never point this at real data).
"""

import asyncio
import io
import os
from collections.abc import Callable, Iterator

import numpy as np
import pytest
from fastapi.testclient import TestClient
from PIL import Image
from sqlalchemy import text

from signalscope.core.config import get_settings
from signalscope.db import create_engine
from signalscope.main import create_app

TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL")


def _reset_postgres(url: str) -> None:
    async def _reset() -> None:
        engine = create_engine(url)
        async with engine.begin() as conn:
            await conn.execute(text("DROP SCHEMA public CASCADE"))
            await conn.execute(text("CREATE SCHEMA public"))
        await engine.dispose()

    asyncio.run(_reset())


@pytest.fixture(autouse=True)
def _test_settings(monkeypatch, tmp_path) -> Iterator[None]:
    """Isolate tests from a developer's local .env and give each test a clean database."""
    if TEST_DATABASE_URL:
        _reset_postgres(TEST_DATABASE_URL)
        database_url = TEST_DATABASE_URL
    else:
        database_url = f"sqlite+aiosqlite:///{(tmp_path / 'test.db').as_posix()}"

    env = {
        "ENVIRONMENT": "test",
        "DETECTOR": "mock",
        "MOCK_LATENCY_MS": "0",
        "DATABASE_URL": database_url,
        "AUTO_MIGRATE": "true",
        "SEED_DEMO_USERS": "false",
        "SECRET_KEY": "test-secret-key-that-is-long-enough-1234567890",
        "ARGON2_TIME_COST": "1",
        "ARGON2_MEMORY_KIB": "1024",
        "COOKIE_SECURE": "false",
        "STORAGE_DIR": str(tmp_path / "files"),
        "RETENTION_ENABLED": "false",
    }
    for key, value in env.items():
        monkeypatch.setenv(key, value)
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture
def client() -> Iterator[TestClient]:
    with TestClient(create_app()) as test_client:  # context manager runs lifespan (migrations etc.)
        yield test_client


@pytest.fixture
def image() -> Image.Image:
    rng = np.random.default_rng(0)
    return Image.fromarray(rng.integers(0, 256, size=(96, 128, 3), dtype=np.uint8))


@pytest.fixture
def encode() -> Callable[..., bytes]:
    """Encode a test image to bytes: encode("PNG", size=(64, 48), mode="RGBA", **save_kwargs)."""

    def _encode(
        fmt: str = "JPEG", size: tuple[int, int] = (128, 96), mode: str = "RGB", **save_kwargs
    ) -> bytes:
        rng = np.random.default_rng(1)
        channels = {"RGB": 3, "RGBA": 4}[mode]
        pixels = rng.integers(0, 256, size=(size[1], size[0], channels), dtype=np.uint8)
        buffer = io.BytesIO()
        Image.fromarray(pixels).save(buffer, format=fmt, **save_kwargs)
        return buffer.getvalue()

    return _encode
