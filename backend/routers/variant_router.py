from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from schemas.variant_schemas import VariantResponse, VariantStatus
from repositories.variant_repository import VariantRepository
from app.dependencies import get_variant_repository 


router = APIRouter(prefix="/variants", tags=["Variants"])


class UpdateStatusRequest(BaseModel):
    status: VariantStatus
    error_message: Optional[str] = None


@router.get("/{variant_id}", response_model=VariantResponse)
async def get_variant_by_id(
    variant_id: str,
    repo: VariantRepository = Depends(get_variant_repository),
):
    """
    Récupère une variante unique par son ID principal.
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
    Liste toutes les variantes associées à un post_id donné.
    """
    return await repo.get_by_post_id(post_id)


@router.patch("/{variant_id}/status", response_model=VariantResponse)
async def update_variant_status(
    variant_id: str,
    body: UpdateStatusRequest,
    repo: VariantRepository = Depends(get_variant_repository),
):
    """
    Mets à jour le statut (et optionnellement le message d'erreur) d'une variante par son ID.
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
    Mets à jour le statut de TOUTES les variantes associées à un post_id.
    """
    return await repo.update_status_by_post_id(
        post_id=post_id,
        status=body.status,
        error_message=body.error_message,
    )