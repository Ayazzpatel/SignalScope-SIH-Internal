"""File storage for scan artefacts (heat-maps, optional images).

Local disk today (a Docker volume); the interface is small enough to back with S3/MinIO later.
Keys are generated server-side as "<user_id>/<scan_id>/<name>" and validated, so no user input reaches a path.
"""

import asyncio
import contextlib
import re
import shutil
import uuid
from pathlib import Path

_KEY = re.compile(r"^[0-9a-f-]{36}/[0-9a-f-]{36}/[a-z]+\.(png|webp)$")


def scan_key(user_id: uuid.UUID, scan_id: uuid.UUID, name: str) -> str:
    return f"{user_id}/{scan_id}/{name}"


class LocalStorage:
    def __init__(self, root: Path) -> None:
        self._root = root.resolve()
        self._root.mkdir(parents=True, exist_ok=True)

    def _path(self, key: str) -> Path:
        if not _KEY.match(key):
            raise ValueError(f"Invalid storage key: {key!r}")
        return self._root / key

    async def put(self, key: str, data: bytes) -> None:
        path = self._path(key)

        def _write() -> None:
            path.parent.mkdir(parents=True, exist_ok=True)
            tmp = path.with_suffix(path.suffix + ".tmp")
            tmp.write_bytes(data)
            tmp.replace(path)  # atomic: readers never see a half-written file

        await asyncio.to_thread(_write)

    async def get(self, key: str) -> bytes | None:
        path = self._path(key)
        try:
            return await asyncio.to_thread(path.read_bytes)
        except FileNotFoundError:
            return None

    async def delete(self, *keys: str | None) -> None:
        paths = [self._path(k) for k in keys if k]

        def _remove() -> None:
            for path in paths:
                path.unlink(missing_ok=True)
                with contextlib.suppress(OSError):  # not empty yet — the other file is still there
                    path.parent.rmdir()  # drop the per-scan folder once empty

        await asyncio.to_thread(_remove)

    async def delete_user(self, user_id: uuid.UUID) -> None:
        await asyncio.to_thread(shutil.rmtree, self._root / str(user_id), True)
