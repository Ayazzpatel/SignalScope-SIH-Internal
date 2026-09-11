from typing import Annotated

from fastapi import APIRouter, File, Request, UploadFile

from signalscope.core.errors import AppError
from signalscope.schemas.analysis import AnalysisResponse

from .deps import AnalysisServiceDep, SettingsDep

router = APIRouter(tags=["analysis"])


@router.post(
    "/analyze",
    response_model=AnalysisResponse,
    summary="Analyse one image",
    responses={
        400: {"description": "Empty file"},
        413: {"description": "File or image dimensions too large"},
        415: {"description": "Not a JPEG, PNG or WebP image"},
        422: {"description": "Corrupt image or missing file field"},
        503: {"description": "Model unavailable, busy or timed out"},
    },
)
async def analyze(
    request: Request,
    file: Annotated[UploadFile, File(description="JPEG, PNG or WebP image.")],
    service: AnalysisServiceDep,
    settings: SettingsDep,
) -> AnalysisResponse:
    """Return a likelihood assessment, heat-map, cues and provenance for one image.

    The image is processed in memory and is not stored.
    """
    try:
        raw = await file.read(settings.max_upload_bytes + 1)
    finally:
        await file.close()
    if len(raw) > settings.max_upload_bytes:
        raise AppError(413, "file_too_large", f"The file exceeds the {settings.max_upload_mb} MB limit.")
    return await service.analyze(raw, request.state.request_id)
