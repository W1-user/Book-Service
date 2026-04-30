from typing import Annotated, Optional
from datetime import datetime
from annotated_types import MinLen, MaxLen
from pydantic import BaseModel, Field, field_validator

class BookCreate(BaseModel):
    title: Annotated[str, MinLen(3), MaxLen(100)]
    author: Annotated[str, MinLen(3), MaxLen(40)]
    description: Optional[str] = Field()
    price: float = Field(gt=0, le=10000)

    isbn: Optional[str] = Field(None, pattern=r'^(97[89])?\d{9}[\dX]$')
    binding: Optional[str] = Field(None, max_length=50)
    publisher: Optional[str] = Field(None, max_length=100)
    year: Optional[int] = Field(None, gt=1450, le=datetime.now().year)

    class Config:
        from_attributes = True

    @field_validator
    @classmethod
    def validate_price(cls, v: float) -> float:
        if v <= 0:
            return ValueError("Price must be positive")
        return round(v, 2)

class BookResponse(BaseModel):
    id: int
    title: str
    author: str
    description: Optional[str] = None
    price: float
    isbn: Optional[str] = None
    binding: Optional[str] = None
    publisher: Optional[str] = None
    year: Optional[int] = None
    is_popular: bool = Field(default=False)
    created_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True

class BookBriefSchema(BaseModel):
    id: int
    title: str
    author: str
    price: float
    
    class Config:
        from_attributes = True