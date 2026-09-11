from fastapi import FastAPI, Request, Response
from starlette.formparsers import MultiPartParser

from signalscope.core.errors import error_response

_MULTIPART_OVERHEAD = 64 * 1024


def register_body_limit(app: FastAPI, max_bytes: int) -> None:
    """Reject oversized requests before parsing, and keep accepted uploads in RAM (never spooled to disk)."""
    MultiPartParser.spool_max_size = max_bytes + _MULTIPART_OVERHEAD
    limit = max_bytes + _MULTIPART_OVERHEAD

    @app.middleware("http")
    async def _body_limit(request: Request, call_next) -> Response:
        length = request.headers.get("content-length")
        if length and length.isdigit() and int(length) > limit:
            return error_response(
                request,
                413,
                "file_too_large",
                f"The upload exceeds the {max_bytes // (1024 * 1024)} MB limit.",
            )
        return await call_next(request)
