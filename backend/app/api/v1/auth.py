import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.jwt import create_access_token, create_refresh_token, decode_token, revoke_token
from app.core.logging import get_logger
from app.core.password import hash_password, verify_password
from app.core.permissions import Role
from app.database.models.audit import Audit
from app.database.models.user import User
from app.database.session import get_db
from app.middleware.rate_limit import check_rate_limit
from app.schemas.user import RefreshRequest, TokenResponse, UserLogin, UserRegister, UserResponse

logger = get_logger(__name__)
router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(body: UserRegister, db: AsyncSession = Depends(get_db), _=Depends(check_rate_limit)):
    existing = await db.execute(select(User).where((User.email == body.email) | (User.username == body.username)))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email or username already exists")

    user = User(
        id=str(uuid.uuid4()),
        email=body.email,
        username=body.username,
        hashed_password=hash_password(body.password),
        role=Role.USER.value,
    )
    db.add(user)
    await db.flush()
    logger.info("user_registered", user_id=user.id, email=body.email)
    return user


@router.post("/login", response_model=TokenResponse)
async def login(body: UserLogin, db: AsyncSession = Depends(get_db), _=Depends(check_rate_limit)):
    result = await db.execute(select(User).where(User.username == body.username))
    user = result.scalar_one_or_none()
    if not user or not verify_password(body.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    db.add(Audit(id=str(uuid.uuid4()), user_id=user.id, action="login", resource="auth"))
    await db.flush()

    logger.info("user_login", user_id=user.id)
    return TokenResponse(
        access_token=create_access_token(user.id),
        refresh_token=create_refresh_token(user.id),
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh(body: RefreshRequest, db: AsyncSession = Depends(get_db)):
    payload = decode_token(body.refresh_token)
    if not payload or payload.get("type") != "refresh":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

    result = await db.execute(select(User).where(User.id == payload["sub"]))
    user = result.scalar_one_or_none()
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found or inactive")

    return TokenResponse(
        access_token=create_access_token(user.id),
        refresh_token=create_refresh_token(user.id),
    )


@router.post("/logout")
async def logout(
    user: User = Depends(get_current_user),
    credentials=Depends(__import__("fastapi.security", fromlist=["HTTPBearer"]).HTTPBearer()),
):
    from jose import jwt

    from app.core.settings import get_settings

    settings = get_settings()
    try:
        payload = jwt.decode(credentials.credentials, settings.secret_key, algorithms=[settings.jwt_algorithm])
        jti = payload.get("jti")
        exp = payload.get("exp")
        if jti:
            await revoke_token(jti, exp)
            logger.info("token_revoked", user_id=user.id, jti=jti)
    except Exception as e:
        logger.warning("logout_token_revoke_failed", error=str(e))

    return {"message": "Logged out successfully"}


@router.get("/me", response_model=UserResponse)
async def get_me(user: User = Depends(get_current_user)):
    return user
