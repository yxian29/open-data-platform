from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError

from shared.config import settings

security = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
) -> dict:
    if credentials is None:
        return {"sub": "anonymous", "role": "viewer"}

    try:
        payload = jwt.decode(
            credentials.credentials,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
        )
        return {"sub": payload.get("sub"), "role": payload.get("role", "viewer")}
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )


def require_role(role: str):
    async def check(user: dict = Depends(get_current_user)):
        roles_hierarchy = {"admin": 3, "analyst": 2, "viewer": 1}
        user_level = roles_hierarchy.get(user.get("role", "viewer"), 0)
        required_level = roles_hierarchy.get(role, 0)
        if user_level < required_level:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return user
    return check
