from pydantic import BaseModel


class UserSettingsResponse(BaseModel):
    theme: str = "dark"
    language: str = "en"
    notifications_enabled: bool = True

    model_config = {"from_attributes": True}


class UserSettingsUpdate(BaseModel):
    theme: str | None = None
    language: str | None = None
    notifications_enabled: bool | None = None
