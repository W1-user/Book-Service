from datetime import timedelta

from book_service.auth import auth

from book_service.config import settings
from book_service.schemas.users import UserSchemas

TOKEN_TYPE_FIELD = "type"
ACCESS_TOKEN_FIELD = "access"
REFRESH_TOKEN_FIELD = "refresh"

def create_jwt(
    token_type: str,
    payload: dict,
    expire_minutes: int = settings.auth.expire_access_token,
    expire_timedelta: timedelta | None = None,
) -> str:
    jwt_payload = {TOKEN_TYPE_FIELD: token_type}
    jwt_payload.update(
        payload
    )
    return auth.encode(
        payload=jwt_payload,
        expire_access_token=expire_minutes,
        expire_timedelta=expire_timedelta,
    )

def create_access_token(user: UserSchemas):
    jwt_payload = {
        "sub": user.username,
        "username": user.username,
        "email": user.email,
    }
    return create_jwt(
        token_type=ACCESS_TOKEN_FIELD,
        payload=jwt_payload,
        expire_minutes=settings.auth.expire_access_token,
    )

def create_refresh_token(user: UserSchemas):
    jwt_payload = {
        "sub": user.username,
    }
    return create_jwt(
        token_type=REFRESH_TOKEN_FIELD,
        payload=jwt_payload,
        expire_timedelta=timedelta(days=settings.auth.expire_refresh_token),
    )