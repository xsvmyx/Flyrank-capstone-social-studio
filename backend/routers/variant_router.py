from typing import List
from fastapi import APIRouter, Depends, HTTPException, status

from schemas.variant_schemas import VariantResponse, UpdateStatusRequest
from repositories.variant_repository import VariantRepository
from app.dependencies import get_variant_repository , get_db
from supabase import Client
from schemas.variant_schemas import VariantStatus
from datetime import datetime, timezone




router = APIRouter(prefix="/variants", tags=["Variants"])



@router.get("/{variant_id}", response_model=VariantResponse)
async def get_variant_by_id(
    variant_id: str,
    repo: VariantRepository = Depends(get_variant_repository),
):
    """
    Retrieves a single variant by its ID.
    """
    variant = await repo.get_by_id(variant_id)

    if not variant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Variant with ID {variant_id} not found",
        )

    return variant


@router.get("/post/{post_id}", response_model=List[VariantResponse])
async def get_variants_by_post_id(
    post_id: str,
    repo: VariantRepository = Depends(get_variant_repository),
):
    """
    Retrieves all variants associated with a given post_id.
    Returns 404 if no variants are found.
    """
    variants = await repo.get_by_post_id(post_id)

    if not variants:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No variants found for post_id '{post_id}'.",
        )

    return variants




@router.patch("/{variant_id}/status", response_model=VariantResponse)
async def update_variant_status(
    variant_id: str,
    body: UpdateStatusRequest,
    supabase: Client = Depends(get_db),
    repo: VariantRepository = Depends(get_variant_repository),
):
    """
    Updates the status of a variant. If status is set to 'scheduled', 
    enqueues a delayed publish job in PGMQ.
    """

    existing_variant = await repo.get_by_id(variant_id)
    if not existing_variant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Variant with ID {variant_id} not found",
        )


    if body.status == VariantStatus.SCHEDULED:
        if existing_variant.status != VariantStatus.APPROVED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot schedule a variant that is not currently approved."
            )
        
        if not body.scheduled_at:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Field 'scheduled_at' is required when scheduling a variant."
            )

        now = datetime.now(timezone.utc)
        if body.scheduled_at <= now:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="'scheduled_at' must be a future timestamp."
            )

        
        delay_seconds = int((body.scheduled_at - now).total_seconds())

    
    updated_variant = await repo.update_status_by_id(
        variant_id=variant_id,
        status=body.status,
        error_message=body.error_message,
        scheduled_at=body.scheduled_at if body.status == VariantStatus.SCHEDULED else None
    )

    
    if body.status == VariantStatus.SCHEDULED:
        try:
           
            payload = {
                "event": "variant.publish",
                "payload": {
                    "variant_id": variant_id,
                    "post_id": str(updated_variant.post_id),
                    "platform": updated_variant.platform.value
                }
            }

            supabase.rpc(
                "pgmq_send",
                {
                    "queue_name": "background_jobs",
                    "msg": payload,
                    "delay": delay_seconds
                }
            ).execute()

        except Exception as e:
            
            await repo.update_status_by_id(variant_id=variant_id, status=VariantStatus.APPROVED)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to enqueue publish job in PGMQ: {str(e)}"
            )

    return updated_variant





@router.patch("/post/{post_id}/status", response_model=List[VariantResponse])
async def update_variants_status_by_post_id(
    post_id: str,
    body: UpdateStatusRequest,
    repo: VariantRepository = Depends(get_variant_repository),
):
    """
    Updates the status of all variants associated with a given post_id.
    Returns 404 if no variants are affected.
    """
    updated_variants = await repo.update_status_by_post_id(
        post_id=post_id,
        status=body.status,
        error_message=body.error_message,
    )

    if not updated_variants:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No variants found or updated for post_id '{post_id}'.",
        )

    return updated_variants