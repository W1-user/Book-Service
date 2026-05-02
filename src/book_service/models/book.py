from sqlalchemy import String, Integer, Float, Text, Boolean
from sqlalchemy.orm import Mapped, mapped_column

from book_service.database import Base


class Book(Base):
    __tablename__ = "Books"

    book_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    author: Mapped[str] = mapped_column(String(40), default="None", nullable=True)
    title: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    price: Mapped[float] = mapped_column(Float, default=0.0)

    isbn: Mapped[str] = mapped_column(String(17), unique=True, nullable=True)
    binding: Mapped[str] = mapped_column(String, nullable=True)
    publisher: Mapped[str] = mapped_column(String, nullable=True)
    year: Mapped[int] = mapped_column(Integer, nullable=True)

    is_popular: Mapped[bool] = mapped_column(Boolean, default=False)

    def __repr__(self) -> str:
        return f"Book - (book_id='{self.book_id}', title='{self.title}', author='{self.author}')"
