from typing import Annotated
from annotated_types import MinLen, MaxLen
from pydantic import BaseModel

class BookCreate(BaseModel):
    title: Annotated[str, MinLen(3), MaxLen(100)]
    author: Annotated[str, MinLen(3), MaxLen(40)]
    description: Annotated[str, MinLen(100), MaxLen(300)]
    price: int

    isbn: Annotated[str, MinLen(13), MaxLen(17)]
    binding: str
    publisher: str
    year: int

    class Config:
        from_attributes = True