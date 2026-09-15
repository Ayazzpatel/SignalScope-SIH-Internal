from typing import Annotated, Any

from fastapi import APIRouter, File, Request, UploadFile

from signalscope.core.errors import AppError
from signalscope.schemas.analysis import AnalysisResponse, EnsembleAnalysisResponse

from .deps import AnalysisServiceDep, SettingsDep

router = APIRouter(tags=["analysis"])

_UPLOAD_ERRORS: dict[int | str, dict[str, Any]] = {
    400: {"description": "Empty file"},
    413: {"description": "File or image dimensions too large"},
    415: {"description": "Not a JPEG, PNG or WebP image"},
    422: {"description": "Corrupt image or missing file field"},
    503: {"description": "Model unavailable, busy or timed out"},
}


async def _read_upload(file: UploadFile, max_bytes: int) -> bytes:
    try:
        raw = await file.read(max_bytes + 1)
    finally:
        await file.close()
    if len(raw) > max_bytes:
        raise AppError(413, "file_too_large", "File exceeds the upload limit.")
    return raw


@router.post(
    "/analyze",
    response_model=AnalysisResponse,
    summary="Analyse one image (E1 model)",
    responses=_UPLOAD_ERRORS,
)
async def analyze(
    request: Request,
    file: Annotated[UploadFile, File(description="JPEG, PNG or WebP image.")],
    service: AnalysisServiceDep,
    settings: SettingsDep,
) -> AnalysisResponse:
    """Return a likelihood assessment from the E1 (Kaggle ConvNeXt-Tiny) model.

    The image is processed in memory and is not stored.
    """
    raw = await _read_upload(file, settings.max_upload_bytes)
    return await service.analyze(raw, request.state.request_id)


@router.post(
    "/analyze/ensemble",
    response_model=EnsembleAnalysisResponse,
    summary="Analyse one image with every model and return one combined verdict",
    responses=_UPLOAD_ERRORS,
)
async def analyze_ensemble(
    request: Request,
    file: Annotated[UploadFile, File(description="JPEG, PNG or WebP image.")],
    service: AnalysisServiceDep,
    settings: SettingsDep,
) -> EnsembleAnalysisResponse:
    """Run E1, Standalone-M and E2 on the same image.

    `final` is decided by a vote of at least ENSEMBLE_MIN_VOTES models (default 2) against
    ENSEMBLE_AI_THRESHOLD (default 0.25); if fewer models are available, all of them must agree.
    With ENSEMBLE_INVERT=true (default) a model votes AI when its P(AI) is at or below the threshold;
    with false, when it is at or above. `models[].ai_probability` is always the raw model output.
    A secondary model that fails is reported in `models[].error` and left out of the decision;
    E1 is required. The image is processed in memory and is not stored.
    """
    raw = await _read_upload(file, settings.max_upload_bytes)
    return await service.analyze_ensemble(raw, request.state.request_id)
