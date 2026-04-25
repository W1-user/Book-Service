from fastapi.security import OAuth2PasswordBearer, HTTPBearer

oauth2_schemas = OAuth2PasswordBearer(
    tokenUrl="/api/v1/Authoriztion/login"
)
http_bearer = HTTPBearer(auto_error=False)