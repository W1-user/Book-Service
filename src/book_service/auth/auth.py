from datetime import datetime, timedelta, timezone
import jwt
import bcrypt
from book_service.config import settings
from typing import Optional

_PRIVATE_KEY_CACHE = None
_PUBLIC_KEY_CACHE = None

def _load_private_key() -> str:
    global _PRIVATE_KEY_CACHE
    if _PRIVATE_KEY_CACHE is None:
        _PRIVATE_KEY_CACHE = settings.auth.private_key_path.read_text()
    return _PRIVATE_KEY_CACHE

def _load_public_key() -> str:
    global _PUBLIC_KEY_CACHE
    if _PUBLIC_KEY_CACHE is None:
        _PUBLIC_KEY_CACHE = settings.auth.public_key_path.read_text()
    return _PUBLIC_KEY_CACHE

def encode(
    payload: dict, 
    algorithm: str = settings.auth.algorithm,
    expire_access_token: int = settings.auth.expire_access_token,
    expire_timedelta: Optional[timedelta] = None
) -> str:
    to_payload = payload.copy()
    now = datetime.now(timezone.utc)

    if expire_timedelta:
        expire = now + expire_timedelta
    else:
        expire = now + timedelta(minutes=expire_access_token)
    
    to_payload.update({
        "exp": int(expire.timestamp()),
        "iat": int(now.timestamp()),
    })
    
    private_key = _load_private_key()
    encoded = jwt.encode(
        payload=to_payload,
        key=private_key,
        algorithm=algorithm,
    )
    return encoded

def decode(
    token: str,
    algorithm: str = settings.auth.algorithm,
) -> dict:
    try:
        public_key = _load_public_key()
        
        decoded = jwt.decode(
            jwt=token,
            key=public_key,
            algorithms=[algorithm],
        )
        return decoded
    except jwt.ExpiredSignatureError as e:
        raise ValueError(f"Token has expired: {e}")
    except jwt.InvalidSignatureError as e:
        raise ValueError(f"Invalid signature: {e}")
    except jwt.InvalidTokenError as e:
        raise ValueError(f"Invalid token: {e}")

def hash_password(password: str) -> str:
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
    return hashed.decode("utf-8")

def verify_password(password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(
        password.encode("utf-8"),
        hashed_password.encode("utf-8")
    )