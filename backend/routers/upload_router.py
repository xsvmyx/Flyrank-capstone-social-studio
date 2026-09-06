from fastapi import APIRouter, Depends, File, UploadFile, status
from app.dependencies import validate_token
from services.upload_service import UploadService
from schemas.upload_schemas import UploadResponse,FileListResponse


router = APIRouter(prefix="/api/v1/media", tags=["Media Upload"])



@router.post("/upload", response_model=UploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_image_endpoint(
    file: UploadFile = File(...),
    user = Depends(validate_token)
):
    upload_service = UploadService()
    image_url = await upload_service.upload_image(file, user_id=user["user"].id)
    return UploadResponse(image_url=image_url)



@router.get("/my-files", response_model=FileListResponse, status_code=status.HTTP_200_OK)
async def list_user_uploads_endpoint(
    user=Depends(validate_token)
):
    """
    Renseigne les fichiers en appliquant strictement les politiques RLS via get_db.
    """
    user_id = user["user"].id if isinstance(user, dict) else user.id
    
    upload_service = UploadService()

    files = await upload_service.list_user_uploads(user_id=user_id)
    return FileListResponse(total=len(files), files=files)