import os
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from book_service.config import settings

engine = create_async_engine(url=settings.db.engine, echo=settings.db.echo)
async_session = async_sessionmaker(bind=engine, expire_on_commit=settings.db.expire_on_commit)

class Base(DeclarativeBase):
    pass

async def get_db():
    async with async_session() as session:
        try:
            yield session
        finally:
            await session.close()