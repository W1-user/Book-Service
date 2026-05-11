from typing import Annotated
from annotated_types import MinLen, MaxLen, Ge
from pydantic import BaseModel, EmailStr


class UserCreate(BaseModel):

    username: Annotated[str, MinLen(3), MaxLen(30)]
    email: EmailStr
    password: Annotated[str, MinLen(8)]
    first_name: Annotated[str, MinLen(1), MaxLen(50)]
    last_name: Annotated[str, MinLen(1), MaxLen(50)]

    class Config:
        from_attributes = True


class UserUpdate(BaseModel):
    username: Annotated[str, MinLen(3), MaxLen(30)] | None = None
    email: EmailStr | None = None
    first_name: Annotated[str, MinLen(1), MaxLen(50)] | None = None
    last_name: Annotated[str, MinLen(1), MaxLen(50)] | None = None
    password: Annotated[str, MinLen(8)] | None = None

    # Admin

    balance: Annotated[float, Ge(0)] | None = None
    is_activity: bool | None = None
    is_moderator: bool | None = None
    is_admin: bool | None = None

    class Config:
        from_attributes = True


class UserSchemas(BaseModel):
    id: int
    username: Annotated[str, MinLen(3), MaxLen(30)]
    email: EmailStr
    first_name: Annotated[str, MinLen(1), MaxLen(50)]
    last_name: Annotated[str, MinLen(1), MaxLen(50)]
    balance: float
    is_activity: bool
    is_moderator: bool
    is_admin: bool

    class Config:
        from_attributes = True


class UserResponse(BaseModel):
    id: int
    username: Annotated[str, MinLen(3), MaxLen(30)]
    email: EmailStr
    first_name: Annotated[str, MinLen(1), MaxLen(50)]
    last_name: Annotated[str, MinLen(1), MaxLen(50)]
    is_activity: bool

    class Config:
        from_attributes = True


class UserProfile(BaseModel):
    id: int
    username: Annotated[str, MinLen(3), MaxLen(30)]
    email: EmailStr
    first_name: Annotated[str, MinLen(1), MaxLen(50)]
    last_name: Annotated[str, MinLen(1), MaxLen(50)]
    balance: float
    is_activity: bool
    is_moderator: bool
    is_admin: bool

    class Config:
        from_attributes = True


class TokenInfo(BaseModel):
    access_token: str
    refresh_token: str | None = None
    token_type: str = "Bearer"


class LoginRequest(BaseModel):
    username: str
    password: str
