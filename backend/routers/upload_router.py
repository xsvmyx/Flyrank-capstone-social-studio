from fastapi import APIRouter, Depends, UploadFile, status
from app.dependencies import get_upload_service, validate_token
from services.upload_service import UploadService
from repositories.storage_repository import StorageRepository
from typing import List

router = APIRouter(prefix="/uploads", tags=["Uploads"])


@router.post("/image", status_code=status.HTTP_201_CREATED)
async def upload_image(
    file: UploadFile,
    current_user: dict = Depends(validate_token),
    upload_service: UploadService = Depends(get_upload_service),
):
    user_id = current_user["user"].id
    signed_url = await upload_service.upload_image(file=file, user_id=user_id)
    return {"url": signed_url}



@router.get("/my-uploads", response_model=List[str])
async def get_my_uploads(
    current_user: dict = Depends(validate_token),
    upload_service: UploadService = Depends(get_upload_service),
):
    """Retrieves the list of file paths uploaded by the currently authenticated user."""
    user_id = current_user["user"].id
    return await upload_service.list_user_uploads(user_id=user_id)