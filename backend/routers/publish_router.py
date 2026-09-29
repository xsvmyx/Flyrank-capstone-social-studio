from fastapi import APIRouter, Depends, HTTPException, status

from app.dependencies import (
    get_publishing_repository,
    get_variant_repository,
    validate_token,
)
from config.settings import logger
from repositories.publish_history_repository import PublishHistoryRepository
from repositories.variant_repository import VariantRepository
from schemas.publish_history_schemas import VariantPublishTriggerRequest
from services.publish_service import PublishService

router = APIRouter(prefix="/publish", tags=["Publishing"])


@router.post("/trigger", status_code=status.HTTP_202_ACCEPTED)
async def trigger_variant_publication(
    payload: VariantPublishTriggerRequest,
    current_user: dict = Depends(validate_token),
    publish_history_repo: PublishHistoryRepository = Depends(
        get_publishing_repository
    ),
    variant_repo: VariantRepository = Depends(get_variant_repository),
):
    try:
        service = PublishService(
            publish_history_repo=publish_history_repo,
            variant_repo=variant_repo,
        )

        new_publish_record = await service.trigger_publication(payload.variant_id)

        return {
            "message": "Publication request accepted and queued successfully.",
            "data": new_publish_record,
        }

    except HTTPException:
        raise
    except ValueError as e:
        logger.error(f"Validation error during publish trigger: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Unexpected error during publish trigger: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to queue publication request: {str(e)}",
        )