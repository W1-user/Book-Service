from datetime import datetime, timezone


from fastapi import (
    APIRouter,
    HTTPException,
    status,
    Depends,
    Query,
)
from sqlalchemy import select, func, and_, desc, asc
from sqlalchemy.ext.asyncio import AsyncSession

from book_service.auth.dependencies import (
    sessionDep,
    current_userDep,
    cacheDep,
)

from book_service.models.user import User
from book_service.models.book import Book
from book_service.models.review import Review, ReviewLike
from book_service.cache import (
    CacheKeys,
    CacheService,
    CacheTTL,
    invalidate_review_cache,
    invalidate_user_reviews_cache,
    invalidate_book_reviews_cache,
    invalidate_all_review_cache,
)
from book_service.schemas.reviews import (
    ReviewSortBy,
    ReviewBase,
    ReviewCreate,
    ReviewResponse,
    ReviewListResponse,
    ReviewAuthorInfo,
    ReviewLikeRequest,
    ReviewLikeResponse,
    ReviewLikesListResponse,
    ReviewModerationRequest,
    ReviewModerationResponse,
    ReviewReportCreate,
    ReviewReportResponse,
    ReviewExistingResponse,
    ReviewSimpleResponse,
    RatingDistribution,
)

router = APIRouter(
    prefix="/reviews",
    tags=["Reviews 📖"],
)


async def update_book_rating(
    session: sessionDep,
    book_id: int,
):
    avg_rating_query = select(func.avg(Review.rating)).where(
        Review.book_id == book_id,
        Review.is_deleted == False,
        Review.is_approved,
    )
    avg_result = await session.execute(avg_rating_query)
    avg_rating = avg_result.scalar() or 0.0

    count_query = select(func.count()).where(
        Review.book_id == book_id,
        Review.is_deleted == False,
        Review.is_approved,
    )
    count_result = await session.execute(count_query)
    reviews_count = count_result.scalar() or 0

    await session.execute(select(Book).where(Book.id == book_id))
    book = await session.get(Book, book_id)
    if book:
        book.avg_rating = round(avg_rating, 2)
        book.reviews_count = reviews_count
        await session.flush()


async def get_ratings_distribution(
    session: sessionDep,
    book_id: int,
):
    query = (
        select(Review.rating, func.count(Review.id))
        .where(
            Review.book_id == book_id,
            Review.is_deleted == False,
            Review.is_approved,
        )
        .group_by(Review.rating)
    )

    result = await session.execute(query)
    distribution = {rating: count for rating, count in result.all()}

    for rating in range(1, 6):
        if rating not in distribution:
            distribution[rating] = 0

    return distribution


async def check_user_liked_view(
    session: sessionDep,
    review_id: int,
    user_id: int,
) -> bool:

    query = select(ReviewLike).where(
        ReviewLike.review_id == review_id,
        ReviewLike.user_id == user_id,
    )
    result = await session.execute(query)
    return result.scalar_one_or_none() is not None


async def get_user_reviews_count(
    session: sessionDep,
    user_id: int,
) -> int:

    query = (
        select(func.count())
        .select_from(Review)
        .where(
            Review.user_id == user_id,
            Review.is_deleted == False,
            Review.is_approved == True,
        )
    )
    result = await session.execute(query)
    count = result.scalar()
    return count or 0


async def get_review_author_info(
    session: sessionDep, review: Review, current_user_id: int | None = None
) -> ReviewResponse:

    author = await session.get(User, review.user_id)

    is_liked = False
    is_own = False

    if current_user_id:
        is_liked = await check_user_liked_view(session, review.id, current_user_id)
        is_own = review.user_id == current_user_id

    return ReviewResponse(
        id=review.id,
        content=review.content,
        rating=review.rating,
        likes_count=review.likes_count,
        is_deleted=review.is_deleted,
        is_approved=review.is_approved,
        user_id=review.user_id,
        book_id=review.book_id,
        created_at=review.created_at,
        author=(
            ReviewAuthorInfo(
                user_id=author.id,
                username=author.username,
                total_reviews=await get_user_reviews_count(session, author.id),
            )
            if author
            else None
        ),
        is_liked_by_current_user=is_liked,
        is_own_review=is_own,
    )


async def get_user_reviews_count(
    session: sessionDep,
    user_id: int,
) -> int:

    query = (
        select(func.count())
        .select_from(Review)
        .where(
            Review.user_id == user_id,
            Review.is_deleted == False,
            Review.is_approved == True,
        )
    )
    result = await session.execute(query)
    return result.scalar() or 0


@router.post(
    "/book/{book_id}",
    response_model=ReviewResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_review(
    session: sessionDep,
    current_user: current_userDep,
    review_data: ReviewCreate,
    book_id: int,
):

    book = await session.get(Book, book_id)
    if not book:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Book is not found!",
        )

    existing_review_query = select(Review).where(
        Review.user_id == current_user.id,
        Review.book_id == book_id,
        Review.is_deleted == False,
    )

    existing_result = await session.execute(existing_review_query)
    existing_review = existing_result.scalar_one_or_none()

    if existing_review:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You message a review!",
        )

    new_review = Review(
        content=review_data.content,
        rating=review_data.rating,
        user_id=current_user.id,
        book_id=book_id,
        created_at=datetime.now(timezone.utc),
    )

    session.add(new_review)
    await session.flush()

    await update_book_rating(session, book_id)

    await session.commit()
    await session.refresh(new_review)

    response = await get_review_author_info(session, new_review, current_user.id)

    return response


@router.get("/book/{book_id}", response_model=ReviewListResponse)
async def get_book_reviews(
    session: sessionDep,
    cache: cacheDep,
    book_id: int,
    skip: int = Query(0, ge=0, description="Count skip reviews"),
    limit: int = Query(20, ge=1, le=100, description="Count reviews in pagination"),
    sort_by: ReviewSortBy = Query(ReviewSortBy.NEWEST, description="Sort"),
):

    cache_key = CacheKeys.book_reviews(book_id, skip, limit, sort_by.value)
    cache_result = await cache.get(cache_key)

    if cache_result:
        return ReviewListResponse(**cache_result)

    book = await session.get(Book, book_id)
    if not book:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Book not found!",
        )

    query = select(Review).where(
        Review.book_id == book_id,
        Review.is_deleted == False,
        Review.is_approved == True,
    )

    if sort_by == ReviewSortBy.NEWEST:
        query = query.order_by(desc(Review.created_at))
    elif sort_by == ReviewSortBy.OLDEST:
        query = query.order_by(asc(Review.created_at))
    elif sort_by == ReviewSortBy.RATING:
        query = query.order_by(desc(Review.rating))
    elif sort_by == ReviewSortBy.LIKES:
        query = query.order_by(desc(Review.likes_count), desc(Review.created_at))

    count_query = select(func.count()).where(
        Review.book_id == book_id,
        Review.is_deleted == False,
        Review.is_approved == True,
    )
    count_result = await session.execute(count_query)
    total = count_result.scalar() or 0

    query = query.offset(skip).limit(limit)
    result = await session.execute(query)
    reviews = result.scalars().all()

    reviews_response = []
    for review in reviews:
        author = await session.get(User, review.user_id)

        review_response = ReviewResponse(
            id=review.id,
            content=review.content,
            rating=review.rating,
            likes_count=review.likes_count,
            is_deleted=review.is_deleted,
            is_approved=review.is_approved,
            user_id=review.user_id,
            book_id=review.book_id,
            created_at=review.created_at,
            author=(
                ReviewAuthorInfo(
                    id=author.id,
                    username=author.username,
                    total_reviews=await get_user_reviews_count(session, author.id),
                )
                if author
                else None
            ),
            is_liked_by_current_user=None,
            is_own_review=False,
        )
        reviews_response.append(review_response)

    distribution_dict = await get_ratings_distribution(session, book_id)
    rating_distribution = RatingDistribution(
        rating_1=distribution_dict.get(1, 0),
        rating_2=distribution_dict.get(2, 0),
        rating_3=distribution_dict.get(3, 0),
        rating_4=distribution_dict.get(4, 0),
        rating_5=distribution_dict.get(5, 0),
    )

    result_data = {
        "total": total,
        "reviews": [r.model_dump() for r in reviews_response],
        "average_rating": round(book.avg_rating or 0, 2),
        "rating_distribution": rating_distribution.model_dump(),
        "skip": skip,
        "limit": limit,
        "has_more": skip + limit < total,
    }

    await cache.set(cache_key, result_data, expire=CacheTTL.REVIEW_LIST)

    return ReviewListResponse(
        total=total,
        reviews=reviews_response,
        average_rating=round(book.avg_rating or 0, 2),
        rating_distribution=rating_distribution,
        skip=skip,
        limit=limit,
        has_more=skip + limit < total,
    )
