from fastapi import APIRouter

from signalscope import __version__
from signalscope.schemas.health import HealthResponse

from .deps import DetectorDep, SettingsDep

router = APIRouter(tags=["system"])


@router.get("/health", response_model=HealthResponse)
def health(settings: SettingsDep, detector: DetectorDep) -> HealthResponse:
    return HealthResponse(
        status="ok" if detector.is_ready else "degraded",
        version=__version__,
        environment=settings.environment,
        detector=detector.name,
        detector_ready=detector.is_ready,
        model_version=detector.model_version,
    )
