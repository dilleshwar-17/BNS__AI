from fastapi import HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.jwt import decode_token

security = HTTPBearer(auto_error=False)


async def verify_token(request: Request) -> dict | None:
    credentials: HTTPAuthorizationCredentials | None = await security(request)
    if not credentials:
        return None
    payload = decode_token(credentials.credentials)
    if payload is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    return payload
