from typing import List
from fastapi import APIRouter, Depends, HTTPException, status

from schemas.variant_schemas import VariantResponse, UpdateStatusRequest
from repositories.variant_repository import VariantRepository
from app.dependencies import get_variant_repository 


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
    repo: VariantRepository = Depends(get_variant_repository),
):
    """
    Updates the status and optionally the error message of a variant by its ID.
    """
    updated_variant = await repo.update_status_by_id(
        variant_id=variant_id,
        status=body.status,
        error_message=body.error_message,
    )

    if not updated_variant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Variant with ID {variant_id} not found",
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