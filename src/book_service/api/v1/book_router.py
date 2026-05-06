from typing import List, Optional
from fastapi import (
    APIRouter,
    HTTPException,
    status,
    Depends,
    Query,
)
from fastapi_cache.decorator import cache

from sqlalchemy import select, delete, update
from sqlalchemy.ext.asyncio import AsyncSession

from book_service.database import get_db
from book_service.schemas.books import BookBriefSchema, BookResponse
from book_service.models.book import Book

from book_service.auth.dependencies import (
    sessionDep,
    cacheDep,
    current_userDep,
)

from book_service.cache import (
    CacheKeys,
    CacheTTL,
    CacheService,
    _get_cached,
)

router = APIRouter(
    prefix="/books",
    tags=["Book 📚"],
)


@router.get("/books", response_model=List[BookResponse])
async def list_books(
    session: sessionDep,
    cache: cacheDep,
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(10, ge=1, le=50, description="Items per page"),
    author: Optional[str] = Query(None, description="Filter by author"),
    title: Optional[str] = Query(None, description="Filter by title"),
) -> List[BookResponse]:

    async def get_books_from_db():
        query = select(Book)

        if author:
            query = query.where(Book.author.ilike(f"%{author}%"))
        if title:
            query = query.where(Book.title.ilike(f"%{title}%"))

        offset = (page - 1) * limit
        query = query.offset(offset).limit(limit).order_by(Book.book_id)

        result = await session.execute(query)
        books = result.scalars().all()

        if not books and page > 1:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No books found on this page",
            )

        return books

    return await cache.get_or_set(
        CacheKeys.book_list(page, limit, author=author, title=title),
        get_books_from_db,
        CacheTTL.BOOK_LIST,
    )


@router.get("/popular", response_model=List[BookBriefSchema])
@cache(expire=CacheTTL.BOOK_LIST)
async def getter_popular_books(
    session: sessionDep,
    cache: cacheDep,
) -> List[BookBriefSchema]:

    async def get_popular_books_from_db():
        result = await session.execute(select(Book).where(Book.is_popular == True))
        books = result.scalars().all()

        if not books:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="No popular books found"
            )

        return books

    return await cache.get_or_set(
        CacheKeys.popular_books(),
        get_popular_books_from_db,
        CacheTTL.BOOK_POPULAR,
    )
