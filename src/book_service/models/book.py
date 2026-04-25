from sqlalchemy import String, Integer, Float, Text, Date
from sqlalchemy.orm import Mapped, mapped_column

from book_service.database import Base

class Book(Base):
    __tablename__ = "Books"

    book_id: Mapped[str] = mapped_column(String)
    author: Mapped[str] = mapped_column(String)
    title: Mapped[str] = mapped_column(String)
    description: Mapped[str] = mapped_column(Text)
    price: Mapped[int] = mapped_column(Float)

    isbn: Mapped[int] = mapped_column(Integer)
    binding: Mapped[str] = mapped_column(String)
    publisher: Mapped[str] = mapped_column(String)
    year: Mapped[int] = mapped_column(Date)