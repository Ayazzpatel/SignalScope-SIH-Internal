import logging

from fastapi import APIRouter, Response
from sqlalchemy import text

from signalscope import __version__
from signalscope.schemas.health import HealthResponse

from .deps import DbDep, DetectorDep, SettingsDep

router = APIRouter(tags=["system"])
logger = logging.getLogger("signalscope")


@router.get("/health", response_model=HealthResponse)
async def health(
    response: Response, settings: SettingsDep, detector: DetectorDep, db: DbDep
) -> HealthResponse:
    try:
        await db.execute(text("SELECT 1"))
        database_ok = True
    except Exception:
        logger.exception("Health check: database unreachable")
        database_ok = False

    healthy = detector.is_ready and database_ok
    if not healthy:
        response.status_code = 503
    return HealthResponse(
        status="ok" if healthy else "degraded",
        version=__version__,
        environment=settings.environment,
        detector=detector.name,
        detector_ready=detector.is_ready,
        model_version=detector.model_version,
        database="ok" if database_ok else "unavailable",
        demo_accounts=settings.seed_demo_users,
    )
