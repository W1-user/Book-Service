import json
from typing import Optional, Awaitable, Callable, TypeVar, Any, Dict, List

from sqlalchemy.orm import DeclarativeBase

from fastapi_cache import FastAPICache
from fastapi_cache.backends.redis import RedisBackend
from redis.asyncio import Redis

from book_service.config import settings

T = TypeVar("T")


def book_serializable(obj: Any) -> Any:
    if isinstance(obj, DeclarativeBase):
        return {c.name: getattr(obj, c.name) for c in obj.__table__.columns}
    if isinstance(obj, list):
        return [book_serializable(item) for item in obj]
    if isinstance(obj, dict):
        return {k: book_serializable(v) for k, v in obj.items()}
    else:
        return obj


class CacheKeys:

    ENTITY_USER = "user"
    ENTITY_BALANCE = "balance"

    ENTITY_BOOK = "book"

    @staticmethod
    def _key(prefix: str, identifier: str) -> str:
        return f"{prefix}:{identifier}"

    @staticmethod
    def _list_key(prefix: str, page: int, limit: int, **filters) -> str:
        filter_parts = []
        for key, value in sorted(filters.items()):
            if value is not None:
                filter_parts.append(f"{key}:{value}")
        filter_str = ":".join(filter_parts)
        base = f"{prefix}:list:{page}:{limit}"
        return f"{base}:{filter_str}" if filter_str else base

    # User

    @staticmethod
    def user(username: str) -> str:
        return CacheKeys._key(CacheKeys.ENTITY_BOOK, username)

    @staticmethod
    def user_by_id(user_id: int) -> str:
        return f"{CacheKeys.ENTITY_USER}:id:{user_id}"

    @staticmethod
    def user_balance(username: str) -> str:
        return CacheKeys._key(CacheKeys.ENTITY_BALANCE, username)

    @staticmethod
    def user_list(
        page: int,
        limit: int,
    ) -> str:
        return f"users:list:{page}:{limit}"

    # Book

    @staticmethod
    def book(book_id: int = None, isbn: int = None) -> str:
        if book_id is not None:
            return CacheKeys._key(CacheKeys.ENTITY_BOOK, f"id:{book_id}")
        if isbn is not None:
            return CacheKeys._key(CacheKeys.ENTITY_BOOK, f"isbn:{isbn}")
        raise ValueError("Either book_id or isbn must be provided")

    @staticmethod
    def book_list(page: int, limit: int, author: str = None, title: str = None) -> str:
        return CacheKeys._list_key(
            CacheKeys.ENTITY_BOOK, page, limit, author=author, title=title
        )

    @staticmethod
    def popular_books(limit: int = 10):
        return f"books:popular:{limit}"


class CacheTTL:

    # Seconds (User)
    USER = 300
    USER_PROFILE = 60
    BALANCE = 60
    USER_LIST = 60
    TEMP = 30

    # Seconds (Book)
    BOOK = 300
    BOOK_LIST = 120
    BOOK_POPULAR = 600
    BOOK_BY_AUTHOR = 300


class CacheService:

    def __init__(self):
        self._backend: Optional[object] = None
        self._enabled: bool = True

    def set_backend(self, backend):
        self._backend = backend

    def disable(self):
        self._enabled = False

    def enable(self):
        self._enabled = True

    async def _safe_operation(
        self, operation: Callable[[], Awaitable[T]], default: T | None = None
    ) -> Optional[T]:
        if not self._enabled or not self._backend:
            return default
        try:
            return await operation()
        except Exception as e:
            return default

    async def get(self, key: str) -> Optional[Any]:
        async def _get():
            value = await self._backend.get(key)
            if value:
                return json.loads(value) if isinstance(value, str) else value
            return None

        return await self._safe_operation(_get)

    async def set(self, key: str, value: Any, expire: int = CacheTTL.USER) -> bool:
        async def _set():
            serializable = book_serializable(value)
            data = json.dumps(serializable, default=str, ensure_ascii=False)
            await self._backend.set(key, data, expire=expire)
            return True

        return await self._safe_operation(_set)

    async def delete(self, key: str) -> bool:
        async def _delete():
            await self._backend.delete(key)
            return True

        return await self._safe_operation(_delete, default=False)

    async def get_or_set(
        self, key: str, func: Callable[[], Awaitable[T]], expire: int = CacheTTL.USER
    ) -> Optional[T]:
        cached = await self.get(key)
        if cached is not None:
            return cached
        result = await func()
        if result:
            await self.set(key, result, expire)
        return result

    async def delete_pattern(self, pattern: str) -> int:
        async def _delete_pattern():
            deleted = 0
            async for key in self._backend.scan_iter(match=pattern):
                await self._backend.delete(key)
                deleted += 1
            return deleted

        return await self._safe_operation(_delete_pattern, default=0)


_cache_service = CacheService()


async def _get_cached() -> CacheService:
    return _cache_service


# Invalidate User cache


async def invalidate_user_cache(username: str):
    await _cache_service.delete(CacheKeys.user(username))
    await _cache_service.delete(CacheKeys.user_balance(username))


async def invalidate_users_list_cache():
    await _cache_service.delete_pattern("users:list:*")


# Invalidate Book cache


async def invalidate_book_cache(book_id: int):
    await _cache_service.delete(CacheKeys.book(book_id))


async def invalidate_book_list_cache():
    await _cache_service.delete_pattern("books:list:*")


async def invalidate_book_popular_list_cache():
    await _cache_service.delete_pattern("books:popular:*")


async def init_cache(redis_client: Redis):
    backend = RedisBackend(redis_client)
    FastAPICache.init(
        backend,
        prefix=settings.cache.prefix,
    )
    _cache_service.set_backend(FastAPICache.get_backend())
