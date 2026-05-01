from fastapi import (
    APIRouter,
    HTTPException,
    status,
    Depends,
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(
    prefix="/reviews",
    tags=["Reviews 📖"],
)
