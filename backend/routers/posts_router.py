from typing import List
from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.dependencies import get_raw_post_repository, validate_token
from config.settings import logger
from repositories.raw_post_repository import RawPostRepository
from schemas.posts_schemas import RawPostCreate, RawPostResponse

router = APIRouter(prefix="/raw-posts", tags=["Raw Posts"])


@router.post("/new", status_code=status.HTTP_201_CREATED)
async def create_raw_post(
    post_data: RawPostCreate,
    current_user: dict = Depends(validate_token),
    raw_post_repo: RawPostRepository = Depends(get_raw_post_repository),
):
    try:
        user_id = current_user["user"].id

        new_post = await raw_post_repo.create(
            post_data=post_data,
            user_id=user_id,
        )

        return {
            "message": "Raw post created successfully",
            "data": new_post,
        }

    except ValueError as e:
        logger.error(f"Validation error during raw post creation: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Unexpected error during raw post creation: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create raw post: {str(e)}",
        )


@router.get("/all", response_model=List[RawPostResponse])
async def get_all_raw_posts(
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    current_user: dict = Depends(validate_token),
    raw_post_repo: RawPostRepository = Depends(get_raw_post_repository),
):
    try:
        posts = await raw_post_repo.get_all(limit=limit, offset=offset)
        return posts
    except Exception as e:
        logger.error(f"Error fetching raw posts: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch raw posts: {str(e)}",
        )


@router.get("/by-title/{title}", response_model=RawPostResponse)
async def get_raw_post_by_title(
    title: str,
    current_user: dict = Depends(validate_token),
    raw_post_repo: RawPostRepository = Depends(get_raw_post_repository),
):
    try:
        post = await raw_post_repo.get_by_title(title=title)
        if not post:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Raw post with title '{title}' not found",
            )
        return post
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching raw post by title '{title}': {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch raw post: {str(e)}",
        )


@router.get("/{post_id}", response_model=RawPostResponse)
async def get_raw_post_by_id(
    post_id: str,
    current_user: dict = Depends(validate_token),
    raw_post_repo: RawPostRepository = Depends(get_raw_post_repository),
):
    try:
        post = await raw_post_repo.get_by_id(post_id=post_id)
        if not post:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Raw post with ID '{post_id}' not found",
            )
        return post
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching raw post #{post_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch raw post: {str(e)}",
        )