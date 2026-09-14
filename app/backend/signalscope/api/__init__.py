from fastapi import APIRouter

from . import account, analyze, auth, health, scans

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(analyze.router)
api_router.include_router(auth.router)
api_router.include_router(scans.router)
api_router.include_router(account.router)
