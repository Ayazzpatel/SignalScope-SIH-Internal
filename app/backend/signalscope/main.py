import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.concurrency import run_in_threadpool
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.engine import make_url

from signalscope import __version__
from signalscope.api import api_router
from signalscope.core.body_limit import register_body_limit
from signalscope.core.config import get_settings
from signalscope.core.csrf import register_csrf_origin_check
from signalscope.core.errors import register_error_handlers
from signalscope.core.rate_limit import RateLimiter
from signalscope.core.request_id import HEADER as REQUEST_ID_HEADER
from signalscope.core.request_id import register_request_id
from signalscope.core.security import PasswordService
from signalscope.db import create_engine, create_sessionmaker
from signalscope.db.migrate import run_migrations
from signalscope.seed import seed_demo_users
from signalscope.services.analysis import AnalysisService
from signalscope.services.auth import AuthService
from signalscope.services.detector import build_detector

logging.basicConfig(level=logging.INFO, format="%(levelname)s:     %(name)s - %(message)s")
logger = logging.getLogger("signalscope")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()

    # Database
    if settings.auto_migrate:
        await run_in_threadpool(run_migrations, settings.database_url)
    engine = create_engine(settings.database_url)
    app.state.sessionmaker = create_sessionmaker(engine)
    logger.info("Database ready (%s)", make_url(settings.database_url).get_backend_name())

    # Auth
    passwords = await run_in_threadpool(
        PasswordService, settings.argon2_time_cost, settings.argon2_memory_kib
    )
    app.state.auth = AuthService(settings, passwords)
    app.state.rate_limiter = RateLimiter()
    if settings.seed_demo_users:
        await seed_demo_users(app.state.sessionmaker, passwords)

    # Detector — model loads once, off the event loop
    detector = build_detector(settings)
    await run_in_threadpool(detector.load)
    app.state.detector = detector
    app.state.analysis = AnalysisService(detector, settings)
    logger.info("Detector '%s' ready (model %s)", detector.name, detector.model_version)

    # Standalone-M — load in parallel (independent of E1)
    try:
        import sys as _sys
        from pathlib import Path as _Path
        _repo_root = str(_Path(__file__).resolve().parents[4])
        if _repo_root not in _sys.path:
            _sys.path.insert(0, _repo_root)
        import importlib as _il
        _sm = _il.import_module("model.predict_standalone")
        standalone_container = await run_in_threadpool(_sm.load_model, settings.ml_device)
        app.state.standalone_model = standalone_container
        app.state.standalone_predict = _sm.predict
        app.state.standalone_version = _sm.MODEL_VERSION
        logger.info("Standalone-M model ready (version %s)", _sm.MODEL_VERSION)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Standalone-M failed to load — dual endpoint will return error: %s", exc)
        app.state.standalone_model = None
        app.state.standalone_predict = None
        app.state.standalone_version = "unavailable"

    try:
        yield
    finally:
        await engine.dispose()


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title=f"{settings.app_name} API",
        version=__version__,
        description="Likelihood assessment of whether an image is real or AI-generated.",
        lifespan=lifespan,
    )
    register_error_handlers(app)

    # Middleware added last runs first: CORS → request ID → CSRF → body limit → routes.
    register_body_limit(app, settings.max_upload_bytes)
    register_csrf_origin_check(app, settings.cors_origins)
    register_request_id(app)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=[REQUEST_ID_HEADER],
    )

    app.include_router(api_router, prefix=settings.api_prefix)
    return app


app = create_app()
