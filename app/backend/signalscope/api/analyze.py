import time
from typing import Annotated

from fastapi import APIRouter, File, Form, Request, UploadFile
from fastapi.concurrency import run_in_threadpool

from signalscope.core.errors import AppError
from signalscope.schemas.analysis import (
    AnalysisResponse,
    Explanation,
    ImageInfo,
    ScanRef,
    StoredResult,
    Timings,
)
from signalscope.services.fingerprint import perceptual_hash
from signalscope.services.heatmap import png_data_url
from signalscope.services.image_io import decode_image
from signalscope.services.scans import clean_filename
from signalscope.services.verdict import DISCLAIMER

from .deps import AnalysisServiceDep, DbDep, OptionalAuthDep, ScanServiceDep, SettingsDep

router = APIRouter(tags=["analysis"])


@router.post(
    "/analyze",
    response_model=AnalysisResponse,
    summary="Analyse one image",
    responses={
        400: {"description": "Empty file"},
        401: {"description": "Access token expired (refresh and retry)"},
        413: {"description": "File or image dimensions too large"},
        415: {"description": "Not a JPEG, PNG or WebP image"},
        422: {"description": "Corrupt image or missing file field"},
        503: {"description": "Model unavailable, busy or timed out"},
    },
)
async def analyze(
    request: Request,
    file: Annotated[UploadFile, File(description="JPEG, PNG or WebP image.")],
    ctx: OptionalAuthDep,
    db: DbDep,
    analysis: AnalysisServiceDep,
    scans: ScanServiceDep,
    settings: SettingsDep,
    save_image: Annotated[
        bool | None,
        Form(description="Signed-in users: keep the image in history. Defaults to the account preference."),
    ] = None,
) -> AnalysisResponse:
    """Return a likelihood assessment, heat-map, cues and provenance for one image.

    Guests: nothing is stored. Signed-in users: the result is saved to their history; the image itself only
    when `save_image` (or their default preference) says so.
    """
    started = time.perf_counter()
    try:
        raw = await file.read(settings.max_upload_bytes + 1)
    finally:
        await file.close()
    if len(raw) > settings.max_upload_bytes:
        raise AppError(413, "file_too_large", f"The file exceeds the {settings.max_upload_mb} MB limit.")

    image = await run_in_threadpool(decode_image, raw, settings.max_image_pixels)
    phash = await run_in_threadpool(perceptual_hash, image.rgb)

    cached = await scans.cached_detection(db, image.sha256, analysis.model_version)
    outcome = await analysis.analyze(image, request.state.request_id, cached)
    user_id = ctx.user.id if ctx else None
    seen = await scans.seen_before(db, user_id, image.sha256, phash, outcome.verdict.band)

    image_info = ImageInfo(
        width=image.width, height=image.height, format=image.format, size_bytes=len(raw), sha256=image.sha256
    )
    stored = StoredResult(
        detector=outcome.detector,
        model_version=outcome.model_version,
        verdict=outcome.verdict,
        cues=outcome.cues,
        attribution=outcome.attribution,
        provenance=outcome.provenance,
        image=image_info,
        timings=Timings(
            inference_ms=outcome.inference_ms, total_ms=round((time.perf_counter() - started) * 1000, 1)
        ),
    )

    scan_ref = None
    if ctx:
        keep_image = ctx.user.save_images_default if save_image is None else save_image
        scan = await scans.save(
            db,
            user_id=ctx.user.id,
            stored=stored,
            sha256=image.sha256,
            phash=phash,
            filename=clean_filename(file.filename),
            heatmap_png=outcome.heatmap_png,
            rgb=image.rgb if keep_image else None,
        )
        scan_ref = ScanRef(id=scan.id, image_saved=scan.image_key is not None)

    return AnalysisResponse(
        request_id=request.state.request_id,
        detector=stored.detector,
        model_version=stored.model_version,
        verdict=stored.verdict,
        explanation=Explanation(
            heatmap_png=png_data_url(outcome.heatmap_png) if outcome.heatmap_png else None, cues=stored.cues
        ),
        attribution=stored.attribution,
        provenance=stored.provenance,
        image=image_info,
        timings=Timings(
            inference_ms=outcome.inference_ms, total_ms=round((time.perf_counter() - started) * 1000, 1)
        ),
        disclaimer=DISCLAIMER,
        cached=outcome.cached,
        scan=scan_ref,
        seen_before=seen,
    )
