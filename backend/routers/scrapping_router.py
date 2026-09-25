from fastapi import APIRouter, Depends, HTTPException, status

from config.settings import logger
from app.dependencies import validate_token, get_scraping_repository
from repositories.scraping_repository import ScrapingRepository
from schemas.scraping_schemas import (
    ScrapingRequestCreate,
    ScrapingRequestResponse,
)


router = APIRouter(prefix="/scraping", tags=["scraping"])


@router.post("/url", status_code=status.HTTP_202_ACCEPTED)
async def upload_url(
    payload: ScrapingRequestCreate,
    current_user: dict = Depends(validate_token),
    scraping_repo: ScrapingRepository = Depends(get_scraping_repository),
):
    """
    Inserts a scraping request into the `scraping_requests` table.
    The PostgreSQL trigger automatically sends the job to PGMQ (`scraping_jobs`).
    """
    user_id = current_user["user"].id

    try:
        scraping_record: ScrapingRequestResponse = await scraping_repo.create(
            request_data=payload,
            user_id=user_id,
        )


        return {
            "message": "Scraping request queued successfully",
            "data": scraping_record,
        }

    except ValueError as e:
        logger.error(
            f"Validation error during scraping request creation: {str(e)}"
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    except Exception as e:
        logger.error(
            f"Unexpected error queuing URL for scraping: {str(e)}"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to queue scraping request: {str(e)}",
        )