from fastapi import (
    APIRouter,
    HTTPException,
    status,
    Depends,
    Form,
)
from sqlalchemy import select, delete, update
from sqlalchemy.ext.asyncio import AsyncSession

from book_service.auth import auth
from book_service.models.user import User
from book_service.schemas.users import UserSchemas, TokenInfo
from book_service.auth.helpers import create_access_token, create_refresh_token
from book_service.database import get_db

UNAUTHED_EXCEPT = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail='User not found!'
)

FORBIDDEN_EXCEPT = HTTPException(
    status_code=status.HTTP_403_FORBIDDEN,
    detail="Error!"
)

router = APIRouter(prefix="/Authorization", tags=["Authorization"])

async def get_user(username: str = Form(), password: str = Form(), session: AsyncSession = Depends(get_db)):
    result = await session.execute(
        select(User).where(User.username == username)
    )
    user = result.scalar_one_or_none()
    if not user:
        raise UNAUTHED_EXCEPT
    if not auth.validate_hash(password=password, hashed_pwd=user.password_hash):
        raise UNAUTHED_EXCEPT
    if not user.is_activity:
        raise FORBIDDEN_EXCEPT
    return UserSchemas.model_validate(user)

@router.post("/login", response_model=TokenInfo)
async def login_user(user: UserSchemas = Depends(get_user)):
    access_token = create_access_token(user)
    refres_token = create_refresh_token(user)

    return TokenInfo(
        access_token=access_token,
        refresh_token=refres_token,
        token_type="Bearer",
    )

# @router.get("/users/me")
# async def getting_for_me