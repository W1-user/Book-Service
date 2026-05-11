import json
from typing import Annotated

from fastapi import Depends, HTTPException, status, Form
from fastapi.security import HTTPBearer, OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from jwt import InvalidTokenError

from book_service.database import get_db
from book_service.models.user import User
from book_service.schemas.users import UserSchemas
from book_service.auth import auth
from book_service.auth.helpers import TOKEN_TYPE_FIELD, ACCESS_TOKEN_FIELD
from book_service.cache import (
    _get_cached,
    CacheService,
    CacheKeys,
    CacheTTL,
    invalidate_user_cache,
)

sessionDep = Annotated[AsyncSession, Depends(get_db)]
cacheDep = Annotated[CacheService, Depends(_get_cached)]

UNAUTHED_EXCEPT = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Could not validate credentials",
    headers={"WWW-Authenticate": "Bearer"},
)

FORBIDDEN_EXCEPT = HTTPException(
    status_code=status.HTTP_403_FORBIDDEN,
    detail="User is not active",
)

BAD_EXCEPT = HTTPException(
    status_code=status.HTTP_400_BAD_REQUEST,
    detail="User with this email or username already exist",
)

oauth2_schemas = OAuth2PasswordBearer(
    tokenUrl="api/v1/authorization/login", auto_error=False
)

http_bearer = HTTPBearer(auto_error=False)


async def get_payload_from_token(token: str = Depends(oauth2_schemas)) -> dict:
    if not token:
        raise UNAUTHED_EXCEPT

    try:
        payload = auth.decode(token)
        return payload
    except InvalidTokenError:
        raise UNAUTHED_EXCEPT


async def get_current_user(
    session: sessionDep,
    cache: cacheDep,
    payload: dict = Depends(get_payload_from_token),
) -> UserSchemas:
    token_type = payload.get(TOKEN_TYPE_FIELD)
    if token_type != ACCESS_TOKEN_FIELD:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token type - {token_type!r} except {ACCESS_TOKEN_FIELD!r}",
        )

    username: str | None = payload.get("username")
    if not username:
        raise UNAUTHED_EXCEPT

    cached_user = await cache.get(CacheKeys.user(username))
    if cached_user:
        return UserSchemas(**cached_user)

    result = await session.execute(select(User).where(User.username == username))
    user = result.scalar_one_or_none()
    if not user:
        raise UNAUTHED_EXCEPT

    user_schema = UserSchemas.model_validate(user)

    await cache.set(CacheKeys.user(username), user_schema.model_dump(), CacheTTL.USER)

    return user_schema


async def get_current_active_user(
    cache: cacheDep,
    user: UserSchemas = Depends(get_current_user),
) -> UserSchemas:
    if not user.is_activity:
        await cache.delete(CacheKeys.user(user.username))
        raise FORBIDDEN_EXCEPT
    return user


async def get_user(
    session: sessionDep,
    cache: cacheDep,
    username: str = Form(),
    password: str = Form(),
):
    cached_user = await cache.get(CacheKeys.user(username))
    if cached_user:
        user = UserSchemas(**cached_user)
        db_user = await session.execute(select(User).where(User.username == username))
        db_user = db_user.scalar_one_or_none()
        if (
            db_user
            and auth.verify_password(password, db_user.password_hash)
            and user.is_activity
        ):
            return user

    result = await session.execute(select(User).where(User.username == username))
    user = result.scalar_one_or_none()
    if not user:
        raise UNAUTHED_EXCEPT
    if not auth.verify_password(password, user.password_hash):
        raise UNAUTHED_EXCEPT
    if not user.is_activity:
        raise FORBIDDEN_EXCEPT
    user_schema = UserSchemas.model_validate(user)

    await cache.set(CacheKeys.user(username), user_schema.model_dump(), CacheTTL.USER)
    return user_schema


async def get_payload_from_token(token: str = Depends(oauth2_schemas)) -> dict:
    try:
        payload = auth.decode(token)
    except InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token!"
        )
    return payload


async def get_user_payload(
    session: sessionDep,
    cache: cacheDep,
    payload: dict = Depends(get_payload_from_token),
) -> UserSchemas:
    token_type = payload.get(TOKEN_TYPE_FIELD)
    if token_type != ACCESS_TOKEN_FIELD:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token type - {token_type!r} except {ACCESS_TOKEN_FIELD!r}",
        )
    username: str | None = payload.get("username")

    cached_user = await cache.get(CacheKeys.user(username))
    if cached_user:
        if isinstance(cached_user, str):
            cached_user = json.loads(cached_user)
        return UserSchemas.model_validate(cached_user)

    result = await session.execute(select(User).where(User.username == username))
    user = result.scalar_one_or_none()
    if not user:
        raise UNAUTHED_EXCEPT

    user_schema = UserSchemas.model_validate(user)

    await cache.set(CacheKeys.user(username), user_schema.model_dump(), CacheTTL.USER)
    return user_schema


async def get_check_user_activity(
    cache: cacheDep,
    user: UserSchemas = Depends(get_user_payload),
):
    if not user.is_activity:
        await invalidate_user_cache(user.username)
        raise FORBIDDEN_EXCEPT
    return user


current_userDep = Annotated[UserSchemas, Depends(get_check_user_activity)]


async def get_current_admin_user(
    user: current_userDep,
) -> UserSchemas:
    if not hasattr(user, "is_admin") or not user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Admin rights required"
        )
    return user


def check_user_access(current_user: UserSchemas, target_user_id: int):
    if current_user.id != target_user_id and not getattr(
        current_user, "is_admin", False
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to access this resource",
        )
