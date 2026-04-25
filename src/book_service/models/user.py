from sqlalchemy import String, Integer, Float
from sqlalchemy.orm import Mapped, mapped_column

from book_service.database import Base

class User(Base):
    __tablename__ = "Users"

    user_id: Mapped[int] = mapped_column(Integer)
    username: Mapped[str] = mapped_column(String)
    email: Mapped[str] = mapped_column(String)
    balance: Mapped[int] = mapped_column(Float)

    first_name: Mapped[str] = mapped_column(String)
    last_name: Mapped[str] = mapped_column(String)