from fastapi import (
    APIRouter,
    HTTPException,
    status,
    Depends,
    Form,
)
from sqlalchemy import select, delete, update
from sqlalchemy.ext.asyncio import AsyncSession
from jwt import InvalidTokenError

from book_service.auth.dependencies import (
    UNAUTHED_EXCEPT,
    FORBIDDEN_EXCEPT,
    BAD_EXCEPT,
    oauth2_schemas,
    http_bearer,
)
from book_service.auth import auth
from book_service.models.user import User
from book_service.schemas.users import UserSchemas, UserCreate, TokenInfo
from book_service.database import get_db 
from book_service.auth.validation import get_user_auth_for_refresh

from book_service.auth.helpers import (
    TOKEN_TYPE_FIELD,
    ACCESS_TOKEN_FIELD,
    REFRESH_TOKEN_FIELD,
    create_access_token,
    create_refresh_token,
)

router = APIRouter(
    prefix="/Authorization", 
    tags=["Authorization⚙️"],
    dependencies=[Depends(http_bearer)]
)

async def get_user(username: str = Form(), password: str = Form(), session: AsyncSession = Depends(get_db)):
    result = await session.execute(
        select(User).where(User.username == username)
    )
    user = result.scalar_one_or_none()
    if not user:
        raise UNAUTHED_EXCEPT
    if not auth.verify_password(password, user.password_hash):
        raise UNAUTHED_EXCEPT
    if not user.is_activity:
        raise FORBIDDEN_EXCEPT
    return UserSchemas.model_validate(user)

async def get_payload_from_token(
        token: str = Depends(oauth2_schemas)
) -> dict:
    try:
        payload = auth.decode(token)
    except InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token!"
        )
    return payload

async def get_user_payload(
        payload: dict = Depends(get_payload_from_token),
        session: AsyncSession = Depends(get_db)
) -> UserSchemas:
    token_type = payload.get(TOKEN_TYPE_FIELD)
    if token_type != ACCESS_TOKEN_FIELD:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token type - {token_type!r} except {ACCESS_TOKEN_FIELD!r}"
        )
    username: str | None = payload.get("sub")
    result = await session.execute(
        select(User).where(User.username == username)
    )
    user = result.scalar_one_or_none()
    if not user:
        raise UNAUTHED_EXCEPT
    
    return UserSchemas.model_validate(user)

async def get_check_user_activity(user: UserSchemas = Depends(get_user_payload)):
    if not user.is_activity:
        raise FORBIDDEN_EXCEPT
    return user

@router.post("/login", response_model=TokenInfo)
async def login_user(user: UserSchemas = Depends(get_user)):
    access_token = create_access_token(user)
    refres_token = create_refresh_token(user)

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
    
    hashed_password = auth.verify_password(password=user_data.password)
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

@router.post("/refresh", response_model=TokenInfo, response_model_exclude_none=True)
async def get_refresh_token(user: UserSchemas = Depends(get_user_auth_for_refresh)):
    access_token = create_access_token(user)
    return TokenInfo(
        access_token=access_token,
    )

@router.get("/users/me")
def getting_for_me(user: UserSchemas = Depends(get_check_user_activity)):
    return {
        "username": user.username,
        "email": user.email,
        "is_activity": True,
    }