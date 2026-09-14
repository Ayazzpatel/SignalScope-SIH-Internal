"""Orchestrates one analysis: decode → [detector ‖ provenance] → verdict → heat-map → response."""

import asyncio
import logging
import time

from fastapi.concurrency import run_in_threadpool
from PIL import Image

from signalscope.core.config import Settings
from signalscope.core.errors import AppError
from signalscope.schemas.analysis import AnalysisResponse, Explanation, ImageInfo, Timings
from signalscope.services.detector import ContractError, Detection, Detector
from signalscope.services.heatmap import render_heatmap_png
from signalscope.services.image_io import decode_image
from signalscope.services.provenance import extract_provenance
from signalscope.services.verdict import DISCLAIMER, assess_agreement, make_verdict

logger = logging.getLogger("signalscope")


class AnalysisService:
    def __init__(self, detector: Detector, settings: Settings) -> None:
        self._detector = detector
        self._settings = settings
        # Caps concurrent model calls so a burst of uploads cannot exhaust CPU/GPU memory.
        self._inference_slots = asyncio.Semaphore(settings.max_concurrent_inference)

    async def analyze(self, raw: bytes, request_id: str) -> AnalysisResponse:
        settings = self._settings
        started = time.perf_counter()

        image = await run_in_threadpool(decode_image, raw, settings.max_image_pixels)

        provenance_task = asyncio.ensure_future(
            run_in_threadpool(extract_provenance, image.raw, image.source, image.mime_type)
        )
        try:
            detection, inference_ms = await self._detect(image.rgb, request_id)
        except BaseException:
            provenance_task.cancel()
            raise
        provenance = await provenance_task

        verdict = make_verdict(detection.prob_ai, settings.band_likely_real_max, settings.band_likely_ai_min)
        assess_agreement(verdict, provenance)

        heatmap_png = None
        if detection.heatmap is not None:
            heatmap_png = await run_in_threadpool(
                render_heatmap_png, detection.heatmap, image.width, image.height, settings.heatmap_max_side
            )

        ai_prob = detection.ai_probability if detection.ai_probability is not None else detection.prob_ai
        real_prob = detection.real_probability if detection.real_probability is not None else round(1.0 - ai_prob, 4)
        label = detection.label if detection.label is not None else ("AI-generated" if ai_prob >= 0.5 else "Real")
        confidence = detection.confidence if detection.confidence is not None else max(ai_prob, real_prob)

        evidence = None
        if detection.evidence is not None:
            evidence = detection.evidence
        else:
            # Generate basic evidence if not provided by detector
            evidence = {
                "image_size": f"{image.width}x{image.height}",
                "sharpness_laplacian_var": 0.0,
                "high_frequency_noise_std": 0.0,
                "exif_present": provenance.exif.present if provenance.exif else False,
            }

        return AnalysisResponse(
            request_id=request_id,
            detector=self._detector.name,
            model_version=detection.model_version,
            label=label,
            ai_probability=ai_prob,
            real_probability=real_prob,
            confidence=confidence,
            evidence=evidence,
            verdict=verdict,
            explanation=Explanation(heatmap_png=heatmap_png, cues=detection.cues),
            attribution=detection.attribution,
            provenance=provenance,
            image=ImageInfo(
                width=image.width,
                height=image.height,
                format=image.format,
                size_bytes=len(raw),
                sha256=image.sha256,
            ),
            timings=Timings(
                inference_ms=round(inference_ms, 1),
                total_ms=round((time.perf_counter() - started) * 1000, 1),
            ),
            disclaimer=DISCLAIMER,
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
