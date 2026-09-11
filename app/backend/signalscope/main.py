import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.concurrency import run_in_threadpool
from fastapi.middleware.cors import CORSMiddleware

from signalscope import __version__
from signalscope.api import api_router
from signalscope.core.config import get_settings
from signalscope.services.detector import build_detector

logging.basicConfig(level=logging.INFO, format="%(levelname)s:     %(name)s - %(message)s")
logger = logging.getLogger("signalscope")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    detector = build_detector(settings)
    await run_in_threadpool(detector.load)  # model loads once, off the event loop
    app.state.detector = detector
    logger.info("Detector '%s' ready (model %s)", detector.name, detector.model_version)
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title=f"{settings.app_name} API",
        version=__version__,
        description="Likelihood assessment of whether an image is real or AI-generated.",
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(api_router, prefix=settings.api_prefix)
    return app


app = create_app()
