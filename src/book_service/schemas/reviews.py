from typing import Annotated, Optional, List, Dict
from annotated_types import MinLen, MaxLen, Ge, Le

from pydantic import BaseModel, Field, field_validator
from datetime import datetime
from enum import Enum

# Enums


class ReviewModerationAction(str, Enum):
    APPROVE = "approve"
    REJECT = "reject"
    DELETE = "delete"
    RESTORE = "restore"


# Base


class ReviewBase(BaseModel):
    content: Annotated[str, MinLen(10), MaxLen(1000)]
    rating: Annotated[int, Ge(1), Le(5)]

    @field_validator("content")
    @classmethod
    def validate_content(cls, v: str) -> str:
        if len(v) < 10:
            raise ValueError("Отзыв должен состоять из 10+ символов")
        if len(v) > 1000:
            raise ValueError("Отзыв должен быть меньше 1000+ символов")
        return v

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "content": "Great book! I really liked the plot and characters.",
                "rating": 5,
            }
        }


class ReviewCreate(ReviewBase):
    pass


# Response Schemas


class ReviewAuthorInfo(BaseModel):
    user_id: int
    username: Annotated[str, MinLen(3), MaxLen(30)]
    # avatar_url
    total_reviews: int = 0

    class Config:
        from_attributes = True


class ReviewResponse(BaseModel):
    id: int
    content: str
    rating: int
    likes_count: int = 0
    is_deleted: bool = False
    is_approved: bool = True
    user_id: int
    book_id: int
    created_at: datetime

    author: ReviewAuthorInfo | None = None
    is_own_review: bool | None = None

    class Config:
        from_attributes = True


# Distribution


class RatingDistribution(BaseModel):
    rating_1: int = 0
    rating_2: int = 0
    rating_3: int = 0
    rating_4: int = 0
    rating_5: int = 0

    @property
    def total(self) -> int:
        return (
            self.rating_1
            + self.rating_2
            + self.rating_3
            + self.rating_4
            + self.rating_5
        )

    @property
    def average(self) -> float:
        if self.total == 0:
            return 0.0

        total_score = (
            self.rating_1 * 1
            + self.rating_2 * 2
            + self.rating_3 * 3
            + self.rating_4 * 4
            + self.rating_5 * 5
        )
        return round(total_score / self.total, 2)


# List Responses


class ReviewListResponse(BaseModel):
    total: int
    reviews: List[ReviewBase]
    average_rating: float
    rating_distribution: RatingDistribution
    skip: bool
    limit: int
    has_more: bool

    @field_validator("has_more", mode="after")
    @classmethod
    def calculate_has_more(cls, v: bool, info) -> bool:
        values = info.data
        return values.get("skip", 0) + len(values.get("reviews", [])) < values.get(
            "total", 0
        )

    class Config:
        from_attributes = True


# Like Repsonses


class ReviewLikeRequest(BaseModel):
    review_id: int

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "review_id": 1,
            }
        }


class ReviewLikeResponse(BaseModel):
    review_id: int
    likes: bool
    total_likes: int
    user_id: int

    class Config:
        from_attributes = True
        json_schemas_extra = {
            "example": {
                "review_id": 1,
                "likes": True,
                "total_likes": 42,
                "user_id": 123,
            }
        }


class ReviewLikesListResponse(BaseModel):
    review_id: int
    total_likes: int
    users: list[dict]
    skip: int
    limit: int
    has_more: bool

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "review_id": 1,
                "total_likes": 42,
                "users": [
                    {"user_id": 1, "username": "WWW1R"},
                    {"user_id": 2, "username": "Francia"},
                ],
                "skip": 28,
                "limit": 100,
                "has_more": True,
            }
        }


# Admin Schemas


class ReviewModerationRequest(BaseModel):
    action: ReviewModerationAction
    reason: Annotated[str, MaxLen(300)] | None = None

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "action": "approve",
                "reason": None,
            }
        }


class ReviewModerationResponse(BaseModel):
    id: int
    action: ReviewModerationAction
    success: bool
    message: str
    moderated_by: str
    moderated_at: datetime

    class Config:
        from_attributes = True


# Report Schemas


class ReviewReportCreate(BaseModel):
    id: int
    reason: Annotated[str, MaxLen(300)]

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "review_id": 1,
                "reason": "Contains obscene language",
            }
        }


class ReviewReportResponse(BaseModel):
    id: int
    review_id: int
    user_id: int
    reason: str
    status: str
    created_at: datetime

    class Config:
        from_attributes = True


# Simple Responses


class ReviewSimpleResponse(BaseModel):
    id: int
    rating: Annotated[float, Ge(1), Le(5)]
    username: Annotated[str, MinLen(3), MaxLen(30)]
    created_at: datetime

    class Config:
        from_attributes = True


class ReviewExistingResponse(BaseModel):
    exist: bool
    review_id: int | None = None
    user_id: int | None = None
    book_id: int | None = None

    class Config:
        from_attributes = True
