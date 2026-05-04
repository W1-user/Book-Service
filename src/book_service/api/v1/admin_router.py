from typing import List, Dict, Optional
from fastapi import (
    APIRouter,
    HTTPException,
    status,
    Depends,
    Query,
)

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from book_service.database import get_db
from book_service.schemas.users import UserSchemas
from book_service.schemas.books import BookCreate, BookResponse
from book_service.models.user import User
from book_service.models.book import Book
from book_service.auth.dependencies import get_current_admin_user, UNAUTHED_EXCEPT
from book_service.cache import (
    _get_cached,
    CacheService,
    CacheKeys,
    CacheTTL,
    invalidate_user_cache,
    invalidate_users_list_cache,
    invalidate_book_cache,
    invalidate_book_list_cache,
    invalidate_book_popular_list_cache,
)

router = APIRouter(
    prefix="/admin", tags=["Admin 👑"], dependencies=[Depends(get_current_admin_user)]
)


# User


@router.get("/users", response_model=List[UserSchemas])
async def get_all_users(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    is_active: bool = None,
    session: AsyncSession = Depends(get_db),
    cache: CacheService = Depends(_get_cached),
):
    query = select(User)

    if is_active is not None:
        query = query.where(User.is_activity == is_active)

    offset = (page - 1) * limit
    query = query.offset(offset).limit(limit).order_by(User.id)

    result = await session.execute(query)
    users = result.scalars().all()

    return users


@router.get("/users/{user_id}", response_model=UserSchemas)
async def get_user_by_id(user_id: int, session: AsyncSession = Depends(get_db)):
    user = await session.get(User, user_id)
    if not user:
        raise UNAUTHED_EXCEPT
    return user


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user_by_id(
    user_id: int,
    session: AsyncSession = Depends(get_db),
    cache: CacheService = Depends(_get_cached),
):
    user = await session.get(User, user_id)
    if not user:
        raise UNAUTHED_EXCEPT

    username = user.username
    await session.delete(user)
    await session.commit()

    await invalidate_user_cache(username)


# Book


@router.post(
    "/create_book", response_model=BookCreate, status_code=status.HTTP_201_CREATED
)
async def create_book(
    book_data: BookCreate,
    session: AsyncSession = Depends(get_db),
    cache: CacheService = Depends(_get_cached),
) -> BookCreate:
    if book_data.isbn:
        existing_book = await session.execute(
            select(Book).where(Book.isbn == book_data.isbn)
        )
        if existing_book.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Book with this ISBN already exist",
            )

    new_book = Book(**book_data.model_dump())

    session.add(new_book)
    await session.commit()
    await session.refresh(new_book)

    await invalidate_book_list_cache()
    await invalidate_book_popular_list_cache()

    return new_book


@router.get("/books/{book_id}", response_model=BookResponse)
async def getter_book_for_id(
    book_id: int,
    session: AsyncSession = Depends(get_db),
    cache: CacheService = Depends(_get_cached),
) -> BookResponse:

    async def get_book_from_db():
        book = await session.get(Book, book_id)

        if not book:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Book - {book_id} not found",
            )
        return book

    return await cache.get_or_set(
        CacheKeys.book(book_id),
        get_book_from_db,
        CacheTTL.BOOK,
    )


@router.put("/books/{book_id}", response_model=BookResponse)
async def update_book(
    book_id: int, book_data: BookCreate, session: AsyncSession = Depends(get_db)
) -> BookResponse:
    book = await session.get(Book, book_id)

    if not book:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Book - {book_id} not found"
        )

    for key, value in book_data.model_dump().items():
        setattr(book, key, value)

    await session.commit()
    await session.refresh(book)

    await invalidate_book_cache(book_id)
    await invalidate_book_list_cache()
    await invalidate_book_popular_list_cache()

    return book


@router.delete("/books/{book_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_book(book_id: int, session: AsyncSession = Depends(get_db)):
    book = await session.get(Book, book_id)

    if not book:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Book - {book_id} not found"
        )
    await session.delete(book)
    await session.commit()

    await invalidate_book_cache(book_id)
    await invalidate_book_list_cache()
    await invalidate_book_popular_list_cache()

    return None


@router.delete("/cache")
async def cache_delete(cache: CacheService = Depends(_get_cached)):
    await cache.delete_pattern("*")
    return {"msg": "Cache clear successfully"}


@router.get("/cache/keys")
async def cache_keys_getter(
    pattern: str = "*", cache: CacheService = Depends(_get_cached)
):
    keys = []
    async for key in cache._backend.scan_iter(match=pattern):
        keys.append(key)
    return {"keys": {keys}, "total": {len(keys)}}


@router.get("/redis/health")
async def check_redis_health(cache: CacheService = Depends(_get_cached)):
    if not cache._enabled or not cache._backend:
        return {
            "status": "❌ disabled",
            "msg": "Redis cache is not available",
        }
    try:
        await cache.set("health:check", {"ok": True}, expire=5)
        result = await cache.get("health:check")
        await cache.delete("health:check")

        return {
            "status": "✅ healthy",
            "msg": "Redis is working",
        }
    except Exception as e:
        return {
            "status": "❌ error",
            "msg": str(e),
        }
