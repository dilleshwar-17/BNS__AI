from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.database.models.settings import UserSettings
from app.database.models.user import User
from app.database.session import get_db
from app.schemas.settings import UserSettingsResponse, UserSettingsUpdate

router = APIRouter(prefix="/settings", tags=["settings"])


@router.get("", response_model=UserSettingsResponse)
async def get_settings(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.scalar(select(UserSettings).where(UserSettings.user_id == user.id))
    if not result:
        return UserSettingsResponse()
    return result


@router.put("", response_model=UserSettingsResponse)
async def update_settings(
    body: UserSettingsUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.scalar(select(UserSettings).where(UserSettings.user_id == user.id))
    if not result:
        result = UserSettings(user_id=user.id)
        db.add(result)

    if body.theme is not None:
        result.theme = body.theme
    if body.language is not None:
        result.language = body.language
    if body.notifications_enabled is not None:
        result.notifications_enabled = body.notifications_enabled

    await db.flush()
    await db.refresh(result)
    return result
