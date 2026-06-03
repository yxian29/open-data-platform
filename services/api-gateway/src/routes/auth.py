from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, HTTPException
from jose import jwt

from shared.config import settings
from shared.models.user import LoginRequest, TokenResponse

router = APIRouter()

DEMO_USERS = {
    "admin": {"password": "admin", "role": "admin"},
    "analyst": {"password": "analyst", "role": "analyst"},
    "viewer": {"password": "viewer", "role": "viewer"},
}


def create_token(username: str, role: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_expiration_minutes)
    payload = {"sub": username, "role": role, "exp": expire}
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


@router.post("/login", response_model=TokenResponse)
async def login(request: LoginRequest):
    user = DEMO_USERS.get(request.username)
    if not user or user["password"] != request.password:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = create_token(request.username, user["role"])
    return TokenResponse(
        access_token=token,
        expires_in=settings.jwt_expiration_minutes * 60,
    )


@router.get("/me")
async def get_current_user_info():
    return {"username": "admin", "role": "admin"}
