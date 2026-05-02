from fastapi import HTTPException, status, Depends
from sqlalchemy import select, delete, update
from sqlalchemy.ext.asyncio import AsyncSession

from jwt import InvalidTokenError

from book_service.auth import auth
from book_service.database import get_db
from book_service.models.user import User
from book_service.schemas.users import UserSchemas
from book_service.auth.dependencies import (
    UNAUTHED_EXCEPT,
    oauth2_schemas,
)
from book_service.auth.helpers import (
    TOKEN_TYPE_FIELD,
    ACCESS_TOKEN_FIELD,
    REFRESH_TOKEN_FIELD,
)


def get_payload_from_token_of_type(token: str = Depends(oauth2_schemas)) -> dict:
    try:
        payload = auth.decode(token)
    except InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token! (user not found)",
        )
    return payload


def validate_token_type(payload: dict, token_type: str) -> bool:
    current_token_type = payload.get(TOKEN_TYPE_FIELD)
    if current_token_type == token_type:
        return True
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=f"Invalid token type - {current_token_type!r} except {token_type!r}",
    )


async def get_user_by_token_sub(payload: dict, session: AsyncSession) -> UserSchemas:
    username: str | None = payload.get("username")
    result = await session.execute(select(User).where(User.username == username))
    user = result.scalar_one_or_none()
    if not user:
        raise UNAUTHED_EXCEPT

    return UserSchemas.model_validate(user)


class UserGetterFromToken:
    def __init__(self, token_type):
        self.token_type = token_type

    async def __call__(
        self,
        payload: dict = Depends(get_payload_from_token_of_type),
        session: AsyncSession = Depends(get_db),
    ):
        validate_token_type(payload, self.token_type)
        return await get_user_by_token_sub(payload, session)


get_user_auth_for_access = UserGetterFromToken(ACCESS_TOKEN_FIELD)
get_user_auth_for_refresh = UserGetterFromToken(REFRESH_TOKEN_FIELD)
