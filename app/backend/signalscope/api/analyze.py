import asyncio
import time
from typing import Annotated

from fastapi import APIRouter, File, Request, UploadFile
from fastapi.concurrency import run_in_threadpool

from signalscope.core.errors import AppError
from signalscope.schemas.analysis import (
    AnalysisResponse,
    DualAnalysisResponse,
    StandaloneResult,
)
from signalscope.services.verdict import make_verdict

from .deps import AnalysisServiceDep, SettingsDep, StandaloneStateDep

router = APIRouter(tags=["analysis"])


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
    """Return a likelihood assessment from the E1 (Kaggle ConvNeXt-Tiny) model.

    The image is processed in memory and is not stored.
    """
    raw = await _read_upload(file, settings.max_upload_bytes)
    return await service.analyze(raw, request.state.request_id)


@router.post(
    "/analyze/dual",
    response_model=DualAnalysisResponse,
    summary="Analyse one image with both E1 and Standalone-M models",
    responses={
        400: {"description": "Empty file"},
        413: {"description": "File or image dimensions too large"},
        415: {"description": "Not a JPEG, PNG or WebP image"},
        422: {"description": "Corrupt image or missing file field"},
        503: {"description": "Model unavailable, busy or timed out"},
    },
)
async def analyze_dual(
    request: Request,
    file: Annotated[UploadFile, File(description="JPEG, PNG or WebP image.")],
    service: AnalysisServiceDep,
    settings: SettingsDep,
    standalone_state: StandaloneStateDep,
) -> DualAnalysisResponse:
    """Run inference with E1 (Kaggle) AND Standalone-M (locally trained) in parallel.

    The two models are fully independent. If Standalone-M fails, its result contains
    an error field and the E1 result is still returned correctly.
    """
    raw = await _read_upload(file, settings.max_upload_bytes)
    standalone_container, standalone_predict_fn, standalone_version = standalone_state

    async def run_standalone() -> StandaloneResult:
        if standalone_container is None or standalone_predict_fn is None:
            verdict = make_verdict(0.5, settings.band_likely_real_max, settings.band_likely_ai_min)
            return StandaloneResult(
                model_version=standalone_version,
                label="Unknown",
                ai_probability=0.5,
                real_probability=0.5,
                confidence=0.5,
                verdict=verdict,
                inference_ms=0.0,
                error="Standalone-M model is not loaded.",
            )
        try:
            from signalscope.services.image_io import decode_image
            img_data = await run_in_threadpool(decode_image, raw, settings.max_image_pixels)
            t0 = time.perf_counter()
            raw_result = await run_in_threadpool(
                standalone_predict_fn, standalone_container, img_data.rgb
            )
            elapsed_ms = (time.perf_counter() - t0) * 1000
            prob_ai = raw_result["ai_probability"]
            verdict = make_verdict(prob_ai, settings.band_likely_real_max, settings.band_likely_ai_min)
            return StandaloneResult(
                model_version=raw_result.get("model_version", standalone_version),
                label=raw_result["label"],
                ai_probability=raw_result["ai_probability"],
                real_probability=raw_result["real_probability"],
                confidence=raw_result["confidence"],
                verdict=verdict,
                inference_ms=round(elapsed_ms, 1),
            )
        except Exception as exc:  # noqa: BLE001
            verdict = make_verdict(0.5, settings.band_likely_real_max, settings.band_likely_ai_min)
            return StandaloneResult(
                model_version=standalone_version,
                label="Error",
                ai_probability=0.5,
                real_probability=0.5,
                confidence=0.5,
                verdict=verdict,
                inference_ms=0.0,
                error=str(exc),
            )

    e1_result, standalone_result = await asyncio.gather(
        service.analyze(raw, request.state.request_id),
        run_standalone(),
    )

    return DualAnalysisResponse(e1=e1_result, standalone=standalone_result)
