from fastapi import (
    APIRouter,
    HTTPException,
    status,
    Depends,
)
from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession

from book_service.models.user import User
from book_service.schemas.users import UserSchemas, UserResponse, UserUpdate
from book_service.auth.dependencies import get_check_user_activity
from book_service.database import get_db

from book_service.auth.dependencies import (
    UNAUTHED_EXCEPT,
    FORBIDDEN_EXCEPT,
    BAD_EXCEPT,
    check_user_access,
)

from book_service.cache import (
    _get_cached,
    CacheKeys,
    CacheService,
    CacheTTL,
    invalidate_user_cache,
)

router = APIRouter(
    prefix="/users",
    tags=["Users 👤"],
)


async def _udpate_user_logic(
    user_id: int,
    user_data: UserUpdate,
    current_user: UserSchemas,
    session: AsyncSession,
    cache: CacheService,
    dependencies=[Depends(check_user_access)],
) -> UserSchemas:
    user = await session.get(User, user_id)
    if not user:
        raise UNAUTHED_EXCEPT

    update_data = user_data.model_dump(exclude_unset=True)
    if not current_user.is_admin:
        allowed_fields = ["first_name", "last_name", "email", "password"]
        forbidden_fields = set(update_data.keys()) - allowed_fields
        if forbidden_fields:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"You cannot update fields: {', '.join(forbidden_fields)}",
            )

    if "password" in update_data:
        from book_service.auth import auth

        user.password_hash = auth.hash_password(update_data.pop("password"))

    for field, value in update_data.items():
        if hasattr(user, field) and value is not None:
            setattr(user, field, value)

    await session.commit()
    await session.refresh(user)

    await invalidate_user_cache(user.username)
    await cache.delete(CacheKeys.user_by_id(user_id))
    await cache.delete_pattern("users:list:*")

    return UserSchemas(
        user_id=user.user_id,
        username=user.username,
        email=user.email,
        first_name=user.first_name,
        last_name=user.last_name,
        balance=user.balance,
        is_activity=user.is_activity,
        is_moderator=user.is_moderator,
        is_admin=user.is_admin,
    )


@router.get(
    "/{user_id}", response_model=UserResponse, dependencies=[Depends(check_user_access)]
)
async def get_user_by_id(
    user_id: int,
    session: AsyncSession = Depends(get_db),
    cache: CacheService = Depends(_get_cached),
):
    async def get_user_from_db():
        user = await session.get(User, user_id)
        if not user:
            raise UNAUTHED_EXCEPT

        return user

    user = await cache.get_or_set(
        CacheKeys.user_by_id(user_id),
        get_user_from_db,
        CacheTTL.USER_PROFILE,
    )

    return UserResponse(
        user_id=user.user_id,
        username=user.username,
        email=user.email,
        first_name=user.first_name,
        last_name=user.last_name,
        is_activity=user.is_activity,
    )


@router.put(
    "/{user_id}", response_model=UserSchemas, dependencies=[Depends(check_user_access)]
)
async def update_user(
    user_id: int,
    user_data: UserUpdate,
    current_user: UserSchemas = Depends(get_check_user_activity),
    session: AsyncSession = Depends(get_db),
    cache: CacheService = Depends(_get_cached),
) -> UserSchemas:
    return await _udpate_user_logic(user_id, user_data, current_user, session, cache)


@router.delete(
    "/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(check_user_access)],
)
async def delete_user(
    user_id: int,
    session: AsyncSession = Depends(get_db),
    cache: CacheService = Depends(_get_cached),
):

    user = await session.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    username = user.username

    await session.delete(user)
    await session.commit()

    await invalidate_user_cache(username)
    await cache.delete(CacheKeys.user_by_id(user_id))
    await cache.delete_pattern("users:list:*")

    return None
