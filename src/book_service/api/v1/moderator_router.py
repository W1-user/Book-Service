from fastapi import (
    APIRouter,
    HTTPException,
    status,
    Depends,
)

router = APIRouter(
    prefix="/moderator",
    tags=["Moderator 👨‍⚖️"],
)
