"""Orchestrates one analysis: [detector (or cache) ‖ provenance] → verdict → heat-map."""

import asyncio
import logging
import time
from dataclasses import dataclass

from fastapi.concurrency import run_in_threadpool
from PIL import Image

from signalscope.core.config import Settings
from signalscope.core.errors import AppError
from signalscope.schemas.analysis import Provenance, Verdict
from signalscope.services.detector import Attribution, ContractError, Cue, Detection, Detector
from signalscope.services.heatmap import render_heatmap_png
from signalscope.services.image_io import DecodedImage
from signalscope.services.provenance import extract_provenance
from signalscope.services.verdict import assess_agreement, make_verdict

logger = logging.getLogger("signalscope")


@dataclass(frozen=True)
class CachedDetection:
    """A previous detector result for a byte-identical image under the same model version."""

    prob_ai: float
    model_version: str
    cues: list[Cue]
    attribution: Attribution | None
    heatmap_png: bytes | None


@dataclass(frozen=True)
class AnalysisOutcome:
    detector: str
    model_version: str
    verdict: Verdict
    cues: list[Cue]
    attribution: Attribution | None
    provenance: Provenance
    heatmap_png: bytes | None
    inference_ms: float
    cached: bool


class AnalysisService:
    def __init__(self, detector: Detector, settings: Settings) -> None:
        self._detector = detector
        self._settings = settings
        # Caps concurrent model calls so a burst of uploads cannot exhaust CPU/GPU memory.
        self._inference_slots = asyncio.Semaphore(settings.max_concurrent_inference)

    @property
    def model_version(self) -> str:
        return self._detector.model_version

    async def analyze(
        self, image: DecodedImage, request_id: str, cached: CachedDetection | None = None
    ) -> AnalysisOutcome:
        settings = self._settings
        provenance_task = asyncio.ensure_future(
            run_in_threadpool(extract_provenance, image.raw, image.source, image.mime_type)
        )
        try:
            if cached:
                prob_ai, model_version = cached.prob_ai, cached.model_version
                cues, attribution, heatmap_png, inference_ms = (
                    cached.cues,
                    cached.attribution,
                    cached.heatmap_png,
                    0.0,
                )
            else:
                detection, inference_ms = await self._detect(image.rgb, request_id)
                prob_ai, model_version = detection.prob_ai, detection.model_version
                cues, attribution = detection.cues, detection.attribution
                heatmap_png = None
                if detection.heatmap is not None:
                    heatmap_png = await run_in_threadpool(
                        render_heatmap_png,
                        detection.heatmap,
                        image.width,
                        image.height,
                        settings.heatmap_max_side,
                    )
        except BaseException:
            provenance_task.cancel()
            raise
        provenance = await provenance_task

        verdict = make_verdict(prob_ai, settings.band_likely_real_max, settings.band_likely_ai_min)
        assess_agreement(verdict, provenance)
        return AnalysisOutcome(
            detector=self._detector.name,
            model_version=model_version,
            verdict=verdict,
            cues=cues,
            attribution=attribution,
            provenance=provenance,
            heatmap_png=heatmap_png,
            inference_ms=round(inference_ms, 1),
            cached=cached is not None,
        )

    async def _detect(self, image: Image.Image, request_id: str) -> tuple[Detection, float]:
        try:
            async with asyncio.timeout(self._settings.inference_timeout_s), self._inference_slots:
                started = time.perf_counter()
                detection = await run_in_threadpool(self._detector.predict, image)
                return detection, (time.perf_counter() - started) * 1000
        except TimeoutError as exc:
            raise AppError(503, "analysis_timeout", "The analysis took too long. Please try again.") from exc
        except ContractError as exc:
            logger.error("ML contract violation (request_id=%s): %s", request_id, exc)
            raise AppError(500, "model_error", "The analysis model returned an invalid result.") from exc
        except AppError:
            raise
        except Exception as exc:
            logger.exception("Detector failed (request_id=%s)", request_id)
            raise AppError(
                503, "analysis_failed", "The analysis model could not process this image."
            ) from exc
