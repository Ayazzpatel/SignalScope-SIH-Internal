import uuid
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Query, Response

from signalscope.core.config import Settings
from signalscope.models import Scan
from signalscope.schemas.analysis import Explanation, StoredResult, VerdictBand
from signalscope.schemas.auth import MessageResponse
from signalscope.schemas.scans import (
    BulkDeleteRequest,
    DeletedResponse,
    ScanDetail,
    ScanListResponse,
    ScanStats,
    ScanSummary,
)
from signalscope.services.scans import SortOrder
from signalscope.services.verdict import DISCLAIMER

from .deps import CurrentAuthDep, DbDep, ScanServiceDep, SettingsDep

router = APIRouter(prefix="/scans", tags=["history"])

_FILE_HEADERS = {"Cache-Control": "private, max-age=300", "X-Content-Type-Options": "nosniff"}


def _url(settings: Settings, scan: Scan, name: str, key: str | None) -> str | None:
    return f"{settings.api_prefix}/scans/{scan.id}/{name}" if key else None


def _summary(settings: Settings, scan: Scan) -> ScanSummary:
    stored = StoredResult.model_validate(scan.result)
    return ScanSummary(
        id=scan.id,
        created_at=scan.created_at,
        filename=scan.filename,
        band=stored.verdict.band,
        prob_ai=stored.verdict.prob_ai,
        headline=stored.verdict.headline,
        image_url=_url(settings, scan, "image", scan.image_key),
        width=stored.image.width,
        height=stored.image.height,
        format=stored.image.format,
        model_version=scan.model_version,
    )


@router.get("", response_model=ScanListResponse, summary="Your scan history (cursor-paginated)")
async def list_scans(
    ctx: CurrentAuthDep,
    db: DbDep,
    scans: ScanServiceDep,
    settings: SettingsDep,
    band: VerdictBand | None = None,
    q: Annotated[str | None, Query(max_length=100, description="Filename contains")] = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    sort: SortOrder = "newest",
    cursor: str | None = None,
    limit: Annotated[int, Query(ge=1, le=60)] = 24,
) -> ScanListResponse:
    items, next_cursor = await scans.list(
        db,
        ctx.user.id,
        band=band,
        query=q,
        date_from=date_from,
        date_to=date_to,
        sort=sort,
        cursor=cursor,
        limit=limit,
    )
    return ScanListResponse(items=[_summary(settings, s) for s in items], next_cursor=next_cursor)


@router.get("/stats", response_model=ScanStats, summary="Totals for the history header")
async def scan_stats(ctx: CurrentAuthDep, db: DbDep, scans: ScanServiceDep) -> ScanStats:
    return ScanStats(**await scans.stats(db, ctx.user.id))


@router.post("/bulk-delete", response_model=DeletedResponse, summary="Delete several scans")
async def bulk_delete(
    body: BulkDeleteRequest, ctx: CurrentAuthDep, db: DbDep, scans: ScanServiceDep
) -> DeletedResponse:
    return DeletedResponse(deleted=await scans.delete_many(db, ctx.user.id, body.ids))


@router.delete("", response_model=DeletedResponse, summary="Delete your entire history")
async def delete_all(ctx: CurrentAuthDep, db: DbDep, scans: ScanServiceDep) -> DeletedResponse:
    return DeletedResponse(deleted=await scans.delete_all(db, ctx.user.id))


@router.get("/{scan_id}", response_model=ScanDetail, summary="One saved scan")
async def get_scan(
    scan_id: uuid.UUID, ctx: CurrentAuthDep, db: DbDep, scans: ScanServiceDep, settings: SettingsDep
) -> ScanDetail:
    scan = await scans.get_owned(db, ctx.user.id, scan_id)
    stored = StoredResult.model_validate(scan.result)
    return ScanDetail(
        id=scan.id,
        created_at=scan.created_at,
        filename=scan.filename,
        image_url=_url(settings, scan, "image", scan.image_key),
        detector=stored.detector,
        model_version=stored.model_version,
        verdict=stored.verdict,
        explanation=Explanation(
            heatmap_png=_url(settings, scan, "heatmap", scan.heatmap_key), cues=stored.cues
        ),
        attribution=stored.attribution,
        provenance=stored.provenance,
        image=stored.image,
        timings=stored.timings,
        disclaimer=DISCLAIMER,
    )


@router.delete("/{scan_id}", response_model=MessageResponse, summary="Delete one scan and its files")
async def delete_scan(
    scan_id: uuid.UUID, ctx: CurrentAuthDep, db: DbDep, scans: ScanServiceDep
) -> MessageResponse:
    await scans.delete(db, ctx.user.id, scan_id)
    return MessageResponse(message="Scan deleted.")


@router.get("/{scan_id}/image", response_class=Response, summary="Saved image (owner only)")
async def scan_image(scan_id: uuid.UUID, ctx: CurrentAuthDep, db: DbDep, scans: ScanServiceDep) -> Response:
    scan = await scans.get_owned(db, ctx.user.id, scan_id)
    data = await scans.read_file(scan.image_key)
    if data is None:
        return Response(status_code=404)
    return Response(content=data, media_type="image/webp", headers=_FILE_HEADERS)


@router.get("/{scan_id}/heatmap", response_class=Response, summary="Heat-map overlay (owner only)")
async def scan_heatmap(scan_id: uuid.UUID, ctx: CurrentAuthDep, db: DbDep, scans: ScanServiceDep) -> Response:
    scan = await scans.get_owned(db, ctx.user.id, scan_id)
    data = await scans.read_file(scan.heatmap_key)
    if data is None:
        return Response(status_code=404)
    return Response(content=data, media_type="image/png", headers=_FILE_HEADERS)
