import json

from fastapi import APIRouter, Response

from signalscope.core.cookies import clear_auth_cookies
from signalscope.core.errors import AppError
from signalscope.db import utcnow
from signalscope.schemas.account import DeleteAccountRequest, PreferencesUpdate
from signalscope.schemas.auth import MessageResponse, UserOut

from .deps import (
    AuthServiceDep,
    CurrentAuthDep,
    DbDep,
    RateLimiterDep,
    ScanServiceDep,
    SettingsDep,
    StorageDep,
)

router = APIRouter(prefix="/account", tags=["account"])


@router.patch("/preferences", response_model=UserOut, summary="Privacy preferences")
async def update_preferences(body: PreferencesUpdate, ctx: CurrentAuthDep, db: DbDep) -> UserOut:
    user = ctx.user
    if body.save_images_default is not None:
        user.save_images_default = body.save_images_default
    if "retention_days" in body.model_fields_set:  # explicit null = keep forever
        user.retention_days = body.retention_days
    await db.commit()
    return UserOut.model_validate(user)


@router.get("/export", summary="Download all your data as JSON")
async def export_data(ctx: CurrentAuthDep, db: DbDep, scans: ScanServiceDep) -> Response:
    payload = await scans.export(db, ctx.user)
    filename = f"signalscope-export-{utcnow():%Y%m%d}.json"
    return Response(
        content=json.dumps(payload, indent=2, ensure_ascii=False),
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="{filename}"', "Cache-Control": "no-store"},
    )


@router.post("/delete", response_model=MessageResponse, summary="Permanently delete your account")
async def delete_account(
    body: DeleteAccountRequest,
    ctx: CurrentAuthDep,
    response: Response,
    db: DbDep,
    auth: AuthServiceDep,
    storage: StorageDep,
    limiter: RateLimiterDep,
    settings: SettingsDep,
) -> MessageResponse:
    limiter.hit(f"delete-account:{ctx.user.id}", 5, 60)
    if not await auth.verify_password(ctx.user, body.password):
        raise AppError(400, "wrong_password", "Password is incorrect.", field="password")

    user_id = ctx.user.id
    await db.delete(ctx.user)  # sessions and scans go with it (ON DELETE CASCADE)
    await db.commit()
    await storage.delete_user(user_id)
    clear_auth_cookies(response, settings)
    return MessageResponse(message="Your account and all its data have been deleted.")
