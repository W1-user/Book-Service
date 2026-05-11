from typing import TYPE_CHECKING
from datetime import datetime

from sqlalchemy import ForeignKey, String, Integer, Boolean, Text, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship

from book_service.database import Base

if TYPE_CHECKING:
    from book_service.models.book import Book
    from book_service.models.user import User


class Review(Base):
    __tablename__ = "reviews"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    rating: Mapped[int] = mapped_column(Integer, nullable=False)
    likes_count: Mapped[int] = mapped_column(Integer, default=0)

    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False)
    is_approved: Mapped[bool] = mapped_column(Boolean, default=True)

    # fk
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    book_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("books.id", ondelete="CASCADE"), nullable=False, index=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    # relationship
    user: Mapped["User"] = relationship(
        "User",
        back_populates="reviews",
        lazy="selectin",
    )
    book: Mapped["Book"] = relationship(
        "Book",
        back_populates="reviews",
        lazy="selectin",
    )

    likes: Mapped[list["ReviewLike"]] = relationship(
        "ReviewLike",
        back_populates="review",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"Review - id={self.id}, user_id={self.user_id}, book_id={self.book_id}, rating={self.rating}"


class ReviewLike(Base):
    __tablename__ = "review_likes"

    # fk

    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        primary_key=True,
        index=True,
    )

    review_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("reviews.id", ondelete="CASCADE"),
        nullable=False,
        primary_key=True,
        index=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    # relationship

    review: Mapped["Review"] = relationship(
        "Review",
        back_populates="likes",
        lazy="selectin",
    )
    user: Mapped["User"] = relationship(
        "User",
        back_populates="review_likes",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"ReviewLike - id={self.id}, user_id={self.user_id}, review_id={self.review_id}"
