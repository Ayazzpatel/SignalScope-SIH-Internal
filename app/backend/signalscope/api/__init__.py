from fastapi import APIRouter

from . import analyze, auth, health

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(analyze.router)
api_router.include_router(auth.router)
