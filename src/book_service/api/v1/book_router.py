from fastapi import (
    APIRouter,
    HTTPException,
    status,
    Depends,
)
from sqlalchemy import select, delete, update
from sqlalchemy.ext.asyncio import AsyncSession

from book_service.database import get_db
from book_service.schemas.books import BookCreate, BookSchemas, BookBriefSchema
from book_service.models.book import Book

router = APIRouter(
    prefix="/Book",
    tags=["Book📚"],
)

@router.post("/create_book", response_model=BookCreate, status_code=status.HTTP_201_CREATED)
async def create_book(
    book_data: BookCreate, 
    session: AsyncSession = Depends(get_db)
):
    if book_data.isbn:
        existing_book = await session.execute(
            select(Book).where(Book.isbn == book_data.isbn)
        )
        if existing_book.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Book with this ISBN already exist"
            )

    new_book = Book(**book_data.model_dump())

    session.add(new_book)
    await session.commit()
    await session.refresh(new_book)

    return new_book

@router.get("/popular_books", response_model=list[BookBriefSchema])
async def getter_popular_books(session: AsyncSession = Depends(get_db)):
    result = await session.execute(
        select(Book).where(Book.is_popular == True)
    )
    books = result.scalars().all()

    if not books:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No popular books found"
        )

    return books