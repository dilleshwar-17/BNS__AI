import uuid
from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt

from app.core.settings import get_settings

settings = get_settings()

BLACKLIST_PREFIX = "jwt:blacklist:"


def create_access_token(subject: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_expire_minutes)
    jti = str(uuid.uuid4())
    now = int(datetime.now(timezone.utc).timestamp())
    return jwt.encode(
        {
            "sub": subject,
            "exp": expire,
            "iat": now,
            "jti": jti,
            "type": "access",
        },
        settings.secret_key,
        algorithm=settings.jwt_algorithm,
    )


def create_refresh_token(subject: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(days=settings.refresh_token_expire_days)
    jti = str(uuid.uuid4())
    now = int(datetime.now(timezone.utc).timestamp())
    return jwt.encode(
        {
            "sub": subject,
            "exp": expire,
            "iat": now,
            "jti": jti,
            "type": "refresh",
        },
        settings.secret_key,
        algorithm=settings.jwt_algorithm,
    )


def decode_token(token: str) -> dict | None:
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.jwt_algorithm])
        return payload
    except JWTError:
        return None


async def revoke_token(jti: str, expires_at: float | None = None):
    try:
        import redis.asyncio as aioredis

        r = aioredis.from_url(settings.redis_url, encoding="utf-8", decode_responses=True)
        ttl = max(int(expires_at - datetime.now(timezone.utc).timestamp()), 60) if expires_at else 86400
        await r.setex(f"{BLACKLIST_PREFIX}{jti}", ttl, "1")
        await r.close()
    except Exception:
        pass


async def is_token_revoked(jti: str) -> bool:
    try:
        import redis.asyncio as aioredis

        r = aioredis.from_url(settings.redis_url, encoding="utf-8", decode_responses=True)
        result = await r.exists(f"{BLACKLIST_PREFIX}{jti}")
        await r.close()
        return bool(result)
    except Exception:
        return False
