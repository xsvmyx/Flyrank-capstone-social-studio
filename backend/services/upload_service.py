import uuid
import logging
from typing import List
from fastapi import UploadFile, HTTPException, status
from storage3.utils import StorageException
from postgrest.exceptions import APIError

from repositories.storage_repository import StorageRepository

logger = logging.getLogger(__name__)


class UploadService:
    def __init__(self, storage_repo: StorageRepository):
        self.storage_repo = storage_repo
        self.allowed_types = ["image/jpeg", "image/png", "image/webp", "image/gif"]

    async def upload_image(self, file: UploadFile, user_id: str) -> str:
        """Validates image MIME type, processes bytes, and delegates upload to repository."""
        if file.content_type not in self.allowed_types:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported image format ({file.content_type}). Allowed formats: JPEG, PNG, WEBP, GIF.",
            )

        try:
            extension = file.filename.split(".")[-1] if file.filename and "." in file.filename else "png"
            file_path = f"{user_id}/{uuid.uuid4()}.{extension}"
            file_bytes = await file.read()

            await self.storage_repo.upload_file(
                file_path=file_path,
                file_bytes=file_bytes,
                content_type=file.content_type,
            )

            return await self.storage_repo.get_signed_url(file_path=file_path)

        except StorageException as e:
            logger.error(f"❌ Storage Error for user {user_id}: {e}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Storage error: {e}",
            )
        except APIError as e:
            logger.error(f"❌ Supabase API error for user {user_id}: {e}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Supabase API error: {e.message}",
            )
        except Exception as e:
            logger.error(f"💥 Unexpected error during upload for user {user_id}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="An internal server error occurred while uploading the image.",
            )


    async def list_user_uploads(self, user_id: str) -> List[str]:
        """Fetches and formats file paths for a given user."""
        try:
            files = await self.storage_repo.list_files(folder_path=user_id)
            return [
                f"{user_id}/{f['name']}"
                for f in files
                if f.get("name") and f.get("name") != ".emptyFolderPlaceholder" and f.get("id") is not None
            ]
        except Exception as e:
            logger.error(f"❌ listing error for user {user_id}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to list your files.",
            )