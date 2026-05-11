from typing import List, TYPE_CHECKING

from sqlalchemy import String, Integer, Float
from sqlalchemy.orm import Mapped, mapped_column, relationship

from book_service.database import Base

if TYPE_CHECKING:
    from book_service.models.review import Review, ReviewLike


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    username: Mapped[str] = mapped_column(String, index=True, unique=True)
    email: Mapped[str] = mapped_column(String, index=True, unique=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    balance: Mapped[float] = mapped_column(Float, default=0.0)

    first_name: Mapped[str] = mapped_column(String(50))
    last_name: Mapped[str] = mapped_column(String(50))

    is_activity: Mapped[bool] = mapped_column(default=True)
    is_moderator: Mapped[bool] = mapped_column(default=False)
    is_admin: Mapped[bool] = mapped_column(default=False)

    reviews: Mapped[List["Review"]] = relationship(
        "Review",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    review_likes: Mapped[List["ReviewLike"]] = relationship(
        "ReviewLike",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    total_reviews: Mapped[int] = mapped_column(Integer, default=0)

    def __repr__(self) -> str:
        return f"User - (user_id='{self.user_id}', username='{self.username}')"
