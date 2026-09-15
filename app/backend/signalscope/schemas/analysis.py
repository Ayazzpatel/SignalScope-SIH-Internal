from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, Field

from signalscope.services.detector.types import Attribution, Cue, EvidenceInfo


class VerdictBand(StrEnum):
    LIKELY_REAL = "likely_real"
    UNCERTAIN = "uncertain"
    LIKELY_AI = "likely_ai"


class BandThresholds(BaseModel):
    likely_real_max: float
    likely_ai_min: float


class Verdict(BaseModel):
    band: VerdictBand
    prob_ai: float = Field(ge=0, le=1, description="Calibrated probability the image is AI-generated.")
    headline: str
    summary: str
    thresholds: BandThresholds


class Explanation(BaseModel):
    heatmap_png: str | None = Field(
        None, description="Transparent PNG overlay as a data URL; same aspect ratio as the image."
    )
    cues: list[Cue]


class SignalSource(StrEnum):
    C2PA = "c2pa"
    XMP = "xmp"
    EXIF = "exif"
    EMBEDDED_TEXT = "embedded_text"
    NONE = "none"


class SignalDirection(StrEnum):
    AI = "ai"
    REAL = "real"
    NEUTRAL = "neutral"


class ProvenanceSignal(BaseModel):
    source: SignalSource
    direction: SignalDirection
    message: str


class ExifInfo(BaseModel):
    present: bool
    camera_make: str | None = None
    camera_model: str | None = None
    lens_model: str | None = None
    software: str | None = None
    captured_at: str | None = None
    has_gps: bool = False  # presence only — coordinates are never returned


class C2PAInfo(BaseModel):
    present: bool
    checked: bool
    validation_state: str | None = None
    claim_generator: str | None = None
    signer: str | None = None
    signed_at: str | None = None
    actions: list[str] = Field(default_factory=list)
    digital_source_types: list[str] = Field(default_factory=list)
    error: str | None = None


class Provenance(BaseModel):
    exif: ExifInfo
    c2pa: C2PAInfo
    signals: list[ProvenanceSignal]
    agreement: Literal["agrees", "conflicts", "model_uncertain", "no_evidence"] = "no_evidence"
    agreement_note: str | None = None


class ImageInfo(BaseModel):
    width: int
    height: int
    format: str
    size_bytes: int
    sha256: str


class Timings(BaseModel):
    inference_ms: float
    total_ms: float


class AnalysisResponse(BaseModel):
    request_id: str
    detector: Literal["mock", "ml"]
    model_version: str
    label: str = "Real"
    ai_probability: float = 0.0
    real_probability: float = 1.0
    confidence: float = 1.0
    evidence: EvidenceInfo | None = None
    verdict: Verdict
    explanation: Explanation
    attribution: Attribution | None
    provenance: Provenance
    image: ImageInfo
    timings: Timings
    disclaimer: str


class ModelScore(BaseModel):
    """One detector's contribution to the combined verdict."""

    key: str
    model_version: str
    ai_probability: float | None = Field(None, ge=0, le=1, description="None when the model failed.")
    inference_ms: float = 0.0
    error: str | None = None


class EnsembleAnalysisResponse(BaseModel):
    """Combined verdict across every detector, plus the primary model's full analysis."""

    final: Verdict = Field(description="The one verdict shown to users.")
    models: list[ModelScore]
    analysis: AnalysisResponse = Field(description="Primary (E1) analysis: image info, evidence, provenance.")
