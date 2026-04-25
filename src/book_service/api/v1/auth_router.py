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
from book_service.schemas.users import UserSchemas, UserCreate, TokenInfo
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

BAD_EXCEPT = HTTPException(
    status_code=status.HTTP_400_BAD_REQUEST,
    detail="User est"
)

router = APIRouter(prefix="/Authorization", tags=["Authorization"])

async def get_user(username: str = Form(), password: str = Form(), session: AsyncSession = Depends(get_db)):
    result = await session.execute(
        select(User).where(User.username == username)
    )
    user = result.scalar_one_or_none()
    if not user:
        raise UNAUTHED_EXCEPT
    if not await auth.validate_hash(password=password, hashed_pwd=user.password_hash):
        raise UNAUTHED_EXCEPT
    if not user.is_activity:
        raise FORBIDDEN_EXCEPT
    return UserSchemas.model_validate(user)

@router.post("/login", response_model=TokenInfo)
async def login_user(user: UserSchemas = Depends(get_user)):
    access_token = await create_access_token(user)
    refres_token = await create_refresh_token(user)

    return TokenInfo(
        access_token=access_token,
        refresh_token=refres_token,
        token_type="Bearer",
    )

@router.post("/register", response_model=UserSchemas, status_code=status.HTTP_201_CREATED)
async def register_user(
    user_data: UserCreate,
    session: AsyncSession = Depends(get_db),
) -> dict:
    res_username = await session.execute(
        select(User).where(User.username == user_data.username)
    )
    username = res_username.scalar_one_or_none()
    if username:
        raise BAD_EXCEPT
    
    res_email = await session.execute(
        select(User).where(User.email == user_data.email)
    )
    email = res_email.scalar_one_or_none()
    if email:
        raise BAD_EXCEPT
    
    hashed_password = await auth.hashed_password(password=user_data.password)
    new_user = User(
        username=user_data.username,
        email=user_data.email,
        password_hash=hashed_password,
        first_name=user_data.first_name,
        last_name=user_data.last_name,
        balance=0.0,
        is_activity=True,
    )
    session.add(new_user)
    await session.commit()
    await session.refresh(new_user)

    return UserSchemas.model_validate(new_user)

# @router.get("/users/me")
# async def getting_for_me(user: UserSchemas = Depends(...)):
    # ...