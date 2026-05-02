import json
from typing import Optional, Awaitable, Callable, TypeVar, Any

from fastapi_cache import FastAPICache
from fastapi_cache.backends.redis import RedisBackend
from redis.asyncio import Redis

from book_service.config import settings

T = TypeVar("T")


class CacheKeys:

    @staticmethod
    def user(username: str) -> str:
        return f"user:{username}"

    @staticmethod
    def user_balance(username: str) -> str:
        return f"balance:{username}"

    @staticmethod
    def user_list(page: int, limit: int) -> str:
        return f"users:list:{page}:{limit}"


class CacheTTL:

    # Seconds
    USER = 300
    BALANCE = 60
    USER_LIST = 60
    TEMP = 30


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
            data = json.dumps(value, default=str, ensure_ascii=False)
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


_cache_service = CacheService()


async def _get_cached() -> CacheService:
    return _cache_service


async def invalidate_user_cache(username: str):
    await _cache_service.delete(CacheKeys.user(username))
    await _cache_service.delete(CacheKeys.user_balance(username))


async def init_cache(redis_client: Redis):
    backend = RedisBackend(redis_client)
    FastAPICache.init(
        backend,
        prefix=settings.cache.prefix,
    )
    _cache_service.set_backend(FastAPICache.get_backend())
