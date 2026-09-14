import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from signalscope.services.detector.types import Attribution

from .analysis import Explanation, ImageInfo, Provenance, Timings, Verdict, VerdictBand


class ScanSummary(BaseModel):
    id: uuid.UUID
    created_at: datetime
    filename: str | None
    band: VerdictBand
    prob_ai: float
    headline: str
    image_url: str | None = Field(description="Owner-only thumbnail URL; null when only the result was kept.")
    width: int
    height: int
    format: str
    model_version: str


class ScanListResponse(BaseModel):
    items: list[ScanSummary]
    next_cursor: str | None


class ScanStats(BaseModel):
    total: int
    by_band: dict[VerdictBand, int]
    this_week: int


class ScanDetail(BaseModel):
    """A saved scan, shaped like an analysis response so the same result view can render it."""

    id: uuid.UUID
    created_at: datetime
    filename: str | None
    image_url: str | None
    detector: Literal["mock", "ml"]
    model_version: str
    verdict: Verdict
    explanation: Explanation
    attribution: Attribution | None
    provenance: Provenance
    image: ImageInfo
    timings: Timings
    disclaimer: str


class BulkDeleteRequest(BaseModel):
    ids: list[uuid.UUID] = Field(min_length=1, max_length=200)


class DeletedResponse(BaseModel):
    deleted: int
