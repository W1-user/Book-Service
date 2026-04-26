from typing import Annotated
from annotated_types import MinLen, MaxLen
from pydantic import BaseModel, EmailStr

class UserCreate(BaseModel):
    username: Annotated[str, MinLen(3), MaxLen(30)]
    email: EmailStr | None = None
    password: Annotated[str, MinLen(8)]
    first_name: Annotated[str, MinLen(3), MaxLen(30)]
    last_name: Annotated[str, MinLen(3), MaxLen(30)]

    class Config:
        from_attributes = True

class UserSchemas(BaseModel):
    username: Annotated[str, MinLen(3), MaxLen(30)]
    email: EmailStr | None = None
    is_activity: bool

    class Config:
        from_attributes = True

class UserResponse(UserSchemas):
    user_id: int

class TokenInfo(BaseModel):
    access_token: str
    refresh_token: str | None = None
    token_type: str = "Bearer"