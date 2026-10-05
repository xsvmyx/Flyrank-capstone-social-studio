from fastapi import APIRouter, Depends, HTTPException, status

from app.dependencies import (
    get_publishing_repository,
    get_variant_repository,
    validate_token,
)
from config.settings import logger
from repositories.publish_history_repository import PublishHistoryRepository
from repositories.variant_repository import VariantRepository
from schemas.publish_history_schemas import (
    BatchPublishJobResult,
    BatchPublishTriggerRequest,
    BatchPublishTriggerResponse,
    VariantPublishTriggerRequest,
)
from schemas.variant_schemas import SocialPlatform
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


@router.post(
    "/trigger-batch",
    response_model=BatchPublishTriggerResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def trigger_batch_publication(
    payload: BatchPublishTriggerRequest,
    current_user: dict = Depends(validate_token),
    publish_history_repo: PublishHistoryRepository = Depends(
        get_publishing_repository
    ),
    variant_repo: VariantRepository = Depends(get_variant_repository),
):
    """
    Triggers publication jobs for all variants matching the given post_id and platforms.
    If 'platforms' is empty or null, it triggers for all available SocialPlatforms.
    """
    try:
        target_platforms = payload.platforms
        if not target_platforms:
            target_platforms = list(SocialPlatform)

        service = PublishService(
            publish_history_repo=publish_history_repo,
            variant_repo=variant_repo,
        )

        results: list[BatchPublishJobResult] = []

        for platform in target_platforms:
            variant = await variant_repo.get_by_post_id_and_platform(
                post_id=payload.post_id,
                platform=platform.value,
            )

            if not variant:
                results.append(
                    BatchPublishJobResult(
                        variant_id="",
                        platform=platform,
                        status="skipped",
                        message=f"No variant found for platform '{platform.value}'.",
                    )
                )
                continue

            try:
                await service.trigger_publication(variant.id)
                results.append(
                    BatchPublishJobResult(
                        variant_id=variant.id,
                        platform=platform,
                        status="queued",
                        message="Publication request queued successfully.",
                    )
                )
            except (HTTPException, ValueError) as pub_err:
  
                error_detail = (
                    pub_err.detail
                    if isinstance(pub_err, HTTPException)
                    else str(pub_err)
                )
                results.append(
                    BatchPublishJobResult(
                        variant_id=variant.id,
                        platform=platform,
                        status="skipped",
                        message=error_detail,
                    )
                )

        queued_count = sum(1 for r in results if r.status == "queued")


        if queued_count == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "message": "No jobs were queued. All variants were either already published, unapproved, or missing.",
                    "post_id": payload.post_id,
                    "results": [r.model_dump() for r in results],
                },
            )

        return BatchPublishTriggerResponse(
            message=f"Batch publish completed: {queued_count}/{len(results)} job(s) queued.",
            post_id=payload.post_id,
            results=results,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error during batch publish trigger: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process batch publication request: {str(e)}",
        )