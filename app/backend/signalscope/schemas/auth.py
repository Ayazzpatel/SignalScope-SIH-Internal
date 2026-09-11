import uuid
from datetime import datetime
from typing import Annotated

from pydantic import AfterValidator, BaseModel, ConfigDict, EmailStr, Field, StringConstraints

from signalscope.models import UserRole


def _normalise_email(value: str) -> str:
    return value.strip().lower()


Email = Annotated[EmailStr, AfterValidator(_normalise_email)]
DisplayName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=80)]
# Length bounds are enforced by the password policy (clear, field-specific messages).
Password = Annotated[str, StringConstraints(max_length=1024)]


class SignupRequest(BaseModel):
    email: Email
    password: Password
    display_name: DisplayName


class LoginRequest(BaseModel):
    email: Email
    password: Password
    remember: bool = False


class ChangePasswordRequest(BaseModel):
    current_password: Password
    new_password: Password


class UpdateProfileRequest(BaseModel):
    display_name: DisplayName


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    display_name: str
    role: UserRole
    created_at: datetime


class AuthResponse(BaseModel):
    user: UserOut


class SessionStateResponse(BaseModel):
    """Bootstrap for the web app: the signed-in user, or null for guests. Never a 401."""

    user: UserOut | None


class SessionOut(BaseModel):
    id: uuid.UUID = Field(description="Session (device) id — the refresh-token family.")
    device: str
    ip_address: str | None
    signed_in_at: datetime
    last_active_at: datetime
    expires_at: datetime
    remember: bool
    current: bool


class SessionListResponse(BaseModel):
    sessions: list[SessionOut]


class MessageResponse(BaseModel):
    message: str
