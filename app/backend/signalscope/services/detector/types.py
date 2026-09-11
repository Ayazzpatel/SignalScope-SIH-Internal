"""Typed form of the ML output contract (docs/ml-contract.md, Section 3)."""

from enum import StrEnum
from typing import Annotated

import numpy as np
from pydantic import BaseModel, ConfigDict, Field, field_validator

Unit = Annotated[float, Field(ge=0.0, le=1.0)]


class CueType(StrEnum):
    FREQUENCY_ARTIFACT = "frequency_artifact"
    TEXTURE_INCONSISTENCY = "texture_inconsistency"
    LIGHTING_INCONSISTENCY = "lighting_inconsistency"
    GEOMETRY_ERROR = "geometry_error"
    WARPED_TEXT = "warped_text"
    ANATOMICAL_ERROR = "anatomical_error"
    NOISE_RESIDUAL = "noise_residual"
    OTHER = "other"


class GeneratorFamily(StrEnum):
    DIFFUSION = "diffusion"
    GAN = "gan"
    OTHER = "other"


class Cue(BaseModel):
    type: CueType
    description: str
    region: tuple[Unit, Unit, Unit, Unit] | None = None  # normalised [x, y, w, h]
    strength: Unit


class Attribution(BaseModel):
    family: GeneratorFamily
    confidence: Unit


class Detection(BaseModel):
    """Validated result of a single detector.predict() call."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    prob_ai: Unit
    model_version: str = Field(min_length=1)
    heatmap: np.ndarray | None = None
    cues: list[Cue] = Field(default_factory=list)
    attribution: Attribution | None = None

    @field_validator("heatmap", mode="before")
    @classmethod
    def _validate_heatmap(cls, value: object) -> np.ndarray | None:
        if value is None:
            return None
        arr = np.asarray(value, dtype=np.float32)
        if arr.ndim != 2 or arr.size == 0:
            raise ValueError(f"heatmap must be a non-empty 2-D array, got shape {arr.shape}")
        if not np.isfinite(arr).all() or arr.min() < 0.0 or arr.max() > 1.0:
            raise ValueError("heatmap values must be finite and within [0, 1]")
        return arr
