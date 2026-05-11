from fastapi import (
    APIRouter,
    HTTPException,
    status,
    Depends,
)
from sqlalchemy import select, delete, update
from sqlalchemy.ext.asyncio import AsyncSession

from book_service.auth.dependencies import http_bearer
from book_service.schemas.users import UserSchemas, UserCreate, TokenInfo
from book_service.auth.validation import get_user_auth_for_refresh
from book_service.database import get_db
from book_service.models.user import User
from book_service.auth import auth

from book_service.auth.dependencies import (
    UNAUTHED_EXCEPT,
    FORBIDDEN_EXCEPT,
    BAD_EXCEPT,
    http_bearer,
    get_user,
    get_check_user_activity,
    sessionDep,
    cacheDep,
    current_userDep,
)

from book_service.cache import (
    _get_cached,
    CacheKeys,
    CacheTTL,
    CacheService,
    invalidate_user_cache,
    invalidate_users_list_cache,
)

from book_service.auth.helpers import create_access_token, create_refresh_token

router = APIRouter(
    prefix="/authorization",
    tags=["Authorization ⚙️"],
    dependencies=[Depends(http_bearer)],
)


@router.post("/login", response_model=TokenInfo)
async def login_user(
    cache: cacheDep,
    user: UserSchemas = Depends(get_user),
):
    access_token = create_access_token(user)
    refres_token = create_refresh_token(user)

    await cache.set(CacheKeys.user(user.username), user.model_dump(), CacheTTL.USER)

    return TokenInfo(
        access_token=access_token,
        refresh_token=refres_token,
        token_type="Bearer",
    )


@router.post(
    "/register", response_model=UserSchemas, status_code=status.HTTP_201_CREATED
)
async def register_user(
    session: sessionDep,
    cache: cacheDep,
    user_data: UserCreate,
) -> dict:
    res_username = await session.execute(
        select(User).where(User.username == user_data.username)
    )
    username = res_username.scalar_one_or_none()
    if username:
        raise BAD_EXCEPT

    res_email = await session.execute(select(User).where(User.email == user_data.email))
    email = res_email.scalar_one_or_none()
    if email:
        raise BAD_EXCEPT

    hashed_password = auth.hash_password(user_data.password)
    new_user = User(
        username=user_data.username,
        email=user_data.email,
        password_hash=hashed_password,
        first_name=user_data.first_name,
        last_name=user_data.last_name,
        balance=0.0,
        is_activity=True,
    )
    session.add(new_user)
    await session.commit()
    await session.refresh(new_user)

    user_schema = UserSchemas.model_validate(new_user)
    await cache.set(CacheKeys.user(username), user_schema.model_dump(), CacheTTL.USER)

    await invalidate_users_list_cache()

    return user_schema


@router.post("/refresh", response_model=TokenInfo, response_model_exclude_none=True)
async def get_refresh_token(
    cache: cacheDep,
    user: UserSchemas = Depends(get_user_auth_for_refresh),
):
    access_token = create_access_token(user)

    await cache.set(CacheKeys.user(user.username), user.model_dump(), CacheTTL.USER)

    return TokenInfo(
        access_token=access_token,
    )


@router.post("/logout")
async def logout(
    user: current_userDep,
    cache: cacheDep,
):
    await invalidate_user_cache(user.username)
    await cache.delete(CacheKeys.user_balance(user.username))

    return {"msg": "Logged out successfully"}


@router.get("/users/me")
async def getting_for_me(
    user: current_userDep,
    cache: cacheDep,
):
    cached_user = await cache.get(CacheKeys.user(user.username))

    if cached_user:
        return {
            "username": cached_user["username"],
            "email": cached_user["email"],
            "is_activity": True,
        }

    return {
        "username": user.username,
        "email": user.email,
        "is_activity": True,
    }
