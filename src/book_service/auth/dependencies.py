from fastapi import (
    HTTPException,
    status
)
from fastapi.security import OAuth2PasswordBearer, HTTPBearer

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

oauth2_schemas = OAuth2PasswordBearer(
    tokenUrl="/api/v1/Authorization/login"
)
http_bearer = HTTPBearer(auto_error=False)