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
from book_service.schemas.books import BookCreate, BookBriefSchema, BookResponse
from book_service.models.book import Book

from book_service.cache import (
    CacheKeys,
    CacheTTL,
    CacheService,
    _get_cached,
    invalidate_book_cache,
    invalidate_book_list_cache,
    invalidate_book_popular_list_cache,
)

router = APIRouter(
    prefix="/book",
    tags=["Book 📚"],
)


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


@router.get("/books", response_model=List[BookResponse])
async def list_books(
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(10, ge=1, le=50, description="Items per page"),
    author: Optional[str] = Query(None, description="Filter by author"),
    title: Optional[str] = Query(None, description="Filter by title"),
    session: AsyncSession = Depends(get_db),
    cache: CacheService = Depends(_get_cached),
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


@router.get("/popular_books", response_model=List[BookBriefSchema])
@cache(expire=CacheTTL.BOOK_LIST)
async def getter_popular_books(
    session: AsyncSession = Depends(get_db),
    cache: CacheService = Depends(_get_cached),
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
