from sqlalchemy import String, Integer, Float
from sqlalchemy.orm import Mapped, mapped_column

from book_service.database import Base

class User(Base):
    __tablename__ = "Users"

    user_id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    username: Mapped[str] = mapped_column(String, index=True, unique=True)
    email: Mapped[str] = mapped_column(String, index=True, unique=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    balance: Mapped[float] = mapped_column(Float, default=0.0)

    first_name: Mapped[str] = mapped_column(String(50))
    last_name: Mapped[str] = mapped_column(String(50))

    def __repr__(self) -> str:
        return f"User - (user_id='{self.user_id}', username='{self.username}')"