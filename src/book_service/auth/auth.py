from datetime import datetime, timedelta, timezone

import jwt
import bcrypt
from book_service.config import settings

_PRIVATE_KEY_CACHE = None
_PUBLIC_KEY_CACHE = None

async def _load_private_key() -> str:
    global _PRIVATE_KEY_CACHE
    if _PRIVATE_KEY_CACHE is None:
        _PRIVATE_KEY_CACHE = settings.auth.private_key_path.read_text()
    return _PRIVATE_KEY_CACHE

async def _load_public_key() -> str:
    global _PUBLIC_KEY_CACHE
    if _PUBLIC_KEY_CACHE is None:
        _PUBLIC_KEY_CACHE = settings.auth.public_key_path.read_text()
    return _PUBLIC_KEY_CACHE

async def encode(
        payload: dict, 
        algorithm: str = settings.auth.algorithm,
        expire_access_token: int = settings.auth.expire_access_token,
        expire_timedelta: timedelta | None=None
) -> str:
    to_payload = payload.copy()
    now = datetime.now(timezone.utc)

    if expire_timedelta:
        expire = now + expire_timedelta
    else:
        expire = now + timedelta(minutes=expire_access_token)
    to_payload.update(
        {
            "exp": int(expire.timestamp()),
            "iat": int(now.timestamp()),
        }
    )
    private_key = await _load_private_key()
    encoded = jwt.encode(
        payload=to_payload,
        key=private_key,
        algorithm=algorithm,
    )
    return encoded

async def decoded(
        token: str,
        algorithm: str = settings.auth.algorithm,
) -> dict:
    
    public_key = await _load_public_key()
    decoded = jwt.decode(
        jwt=token,
        key=public_key,
        algorithms=[algorithm],        
    )
    return decoded

async def hashed_password(
        password: str,
) -> bytes:
    enc_password = password.encode("utf-8")
    salt = bcrypt.gensalt()
    hashed_pwd = bcrypt.hashpw(password=enc_password, salt=salt)
    return hashed_pwd.decode("utf-8")

async def validate_hash(
        password: str,
        hashed_pwd: str,
) -> bool:
    enc_password = password.encode("utf-8")
    if isinstance(hashed_pwd, bytes):
        hashed_pwd = hashed_pwd.decode("utf-8")

    hashed_bytes = hashed_pwd.encode("utf-8")
    bcrypt.checkpw(password=enc_password, hashed_password=hashed_bytes)