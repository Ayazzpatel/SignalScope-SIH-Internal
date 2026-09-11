"""Uniform error envelope: every failure returns {"error": {"code", "message", "request_id", "field"?}}."""

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger("signalscope")


class AppError(Exception):
    def __init__(
        self,
        status_code: int,
        code: str,
        message: str,
        *,
        field: str | None = None,
        headers: dict[str, str] | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message
        self.field = field
        self.headers = headers


def error_response(
    request: Request,
    status_code: int,
    code: str,
    message: str,
    *,
    field: str | None = None,
    headers: dict[str, str] | None = None,
) -> JSONResponse:
    error: dict[str, str | None] = {
        "code": code,
        "message": message,
        "request_id": getattr(request.state, "request_id", None),
    }
    if field:
        error["field"] = field
    return JSONResponse(status_code=status_code, content={"error": error}, headers=headers)


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def _app_error(request: Request, exc: AppError) -> JSONResponse:
        return error_response(
            request, exc.status_code, exc.code, exc.message, field=exc.field, headers=exc.headers
        )

    @app.exception_handler(RequestValidationError)
    async def _validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
        first = exc.errors()[0] if exc.errors() else {}
        field = ".".join(str(part) for part in first.get("loc", ()) if part not in ("body", "query"))
        detail = str(first.get("msg", "invalid input")).removeprefix("Value error, ")
        message = f"{field}: {detail}" if field else "Invalid request."
        return error_response(request, 422, "invalid_request", message, field=field or None)

    @app.exception_handler(StarletteHTTPException)
    async def _http_error(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        return error_response(request, exc.status_code, "http_error", str(exc.detail))

    @app.exception_handler(Exception)
    async def _unhandled(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("Unhandled error (request_id=%s)", getattr(request.state, "request_id", None))
        return error_response(request, 500, "internal_error", "Something went wrong on our side.")
