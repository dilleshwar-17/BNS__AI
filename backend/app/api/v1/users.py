from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.logging import get_logger
from app.core.password import hash_password, verify_password
from app.database.models.user import User
from app.database.session import get_db
from app.schemas.user import UserResponse, UserUpdate

logger = get_logger(__name__)
router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserResponse)
async def get_me(user: User = Depends(get_current_user)):
    return user


@router.put("/me", response_model=UserResponse)
async def update_me(body: UserUpdate, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    if body.email:
        existing = await db.execute(
            __import__("sqlalchemy", fromlist=["select"])
            .select(User)
            .where(User.email == body.email, User.id != user.id)
        )
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already in use")
        user.email = body.email

    if body.full_name is not None:
        user.full_name = body.full_name

    if body.new_password:
        if not body.current_password:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Current password required")
        if not verify_password(body.current_password, user.hashed_password):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Current password is incorrect")
        user.hashed_password = hash_password(body.new_password)
        logger.info("password_changed", user_id=user.id)

    await db.flush()
    logger.info("user_profile_updated", user_id=user.id)
    return user
