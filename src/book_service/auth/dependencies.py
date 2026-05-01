from typing import Optional
from fastapi import (
    HTTPException,
    status,
    Depends,
)
from fastapi.security import (
    OAuth2PasswordBearer,
    HTTPBearer,
    HTTPAuthorizationCredentials,
)
from book_service.auth.auth import decode

UNAUTHED_EXCEPT = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found!"
)

FORBIDDEN_EXCEPT = HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Error!")

BAD_EXCEPT = HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User est")

oauth2_schemas = OAuth2PasswordBearer(
    tokenUrl="/api/v1/authorization/login", auto_error=False
)
http_bearer = HTTPBearer(auto_error=False)

# async def get_current_user(
#         credentials: Optional[HTTPAuthorizationCredentials] = Depends(http_bearer)
# ):
#     if not credentials:
#         raise UNAUTHED_EXCEPT

#     token = credentials.credentials

#     payload = decode(token)
#     if not payload:
#         raise UNAUTHED_EXCEPT

#     user_id = payload.get("sub")
#     if not user_id:
#         raise UNAUTHED_EXCEPT
