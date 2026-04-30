from contextlib import asynccontextmanager
from fastapi import FastAPI
import uvicorn

from book_service.config import settings
from book_service.api.v1.auth_router import router as auth_router
from book_service.api.v1.book_router import router as book_router

from book_service.database import Base, engine

@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    await engine.dispose()

app = FastAPI(title="Book Service", lifespan=lifespan)
app.include_router(auth_router, prefix=settings.default_prefix)
app.include_router(book_router, prefix=settings.default_prefix)

if __name__ == "__main__":
    uvicorn.run(app="main:app", reload=True)