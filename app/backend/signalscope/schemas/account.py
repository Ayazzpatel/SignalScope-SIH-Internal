from typing import Literal

from pydantic import BaseModel, Field

RetentionDays = Literal[7, 30, 90, 365]


class PreferencesUpdate(BaseModel):
    """Partial update. Omit a field to leave it unchanged; `retention_days: null` means keep forever."""

    save_images_default: bool | None = None
    retention_days: RetentionDays | None = None


class DeleteAccountRequest(BaseModel):
    password: str = Field(max_length=1024)
