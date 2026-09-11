import re
import uuid

from fastapi import FastAPI, Request, Response

HEADER = "X-Request-ID"
_VALID = re.compile(r"^[A-Za-z0-9._-]{1,64}$")


def register_request_id(app: FastAPI) -> None:
    @app.middleware("http")
    async def _request_id(request: Request, call_next) -> Response:
        incoming = request.headers.get(HEADER, "")
        request_id = incoming if _VALID.match(incoming) else uuid.uuid4().hex
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers[HEADER] = request_id
        return response
