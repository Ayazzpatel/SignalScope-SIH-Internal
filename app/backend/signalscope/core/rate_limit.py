"""Small in-memory sliding-window rate limiter.

Per-process by design (one uvicorn worker in this deployment). For multiple instances, swap the storage
for Redis behind the same interface.
"""

import math
import time
from collections import defaultdict, deque

from fastapi import Request

from signalscope.core.errors import AppError


class RateLimiter:
    def __init__(self) -> None:
        self._hits: dict[str, deque[float]] = defaultdict(deque)

    def hit(self, key: str, limit: int, window_s: float) -> None:
        now = time.monotonic()
        hits = self._hits[key]
        while hits and hits[0] <= now - window_s:
            hits.popleft()
        if len(hits) >= limit:
            retry_after = math.ceil(hits[0] + window_s - now)
            raise AppError(
                429,
                "rate_limited",
                f"Too many attempts. Please wait {retry_after} seconds and try again.",
                headers={"Retry-After": str(retry_after)},
            )
        hits.append(now)


def client_ip(request: Request) -> str:
    # uvicorn runs with --proxy-headers behind nginx, so request.client is the real client address.
    return request.client.host if request.client else "unknown"
