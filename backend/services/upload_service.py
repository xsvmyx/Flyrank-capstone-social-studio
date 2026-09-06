import uuid
from fastapi import UploadFile, HTTPException, status
from storage3.utils import StorageException
from postgrest.exceptions import APIError
from app.database import supabase_admin
from config.settings import logger
from typing import List
from supabase import Client

class UploadService:
    def __init__(self):
        self.supabase = supabase_admin
        self.bucket_name = "post-media"

    async def upload_image(self, file: UploadFile, user_id: str) -> str:
        allowed_types = ["image/jpeg", "image/png", "image/webp", "image/gif"]
        if file.content_type not in allowed_types:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported image format ({file.content_type}). Allowed formats: JPEG, PNG, WEBP, GIF."
            )

        try:
            extension = file.filename.split(".")[-1] if file.filename and "." in file.filename else "png"
            file_path = f"{user_id}/{uuid.uuid4()}.{extension}"
            file_bytes = await file.read()

            
            self.supabase.storage.from_(self.bucket_name).upload(
                path=file_path,
                file=file_bytes,
                file_options={
                    "content-type": file.content_type,
                    "x-upsert": "true"
                }
            )

            
            res = self.supabase.storage.from_(self.bucket_name).create_signed_url(
                path=file_path,
                expires_in=3600
            )

            if isinstance(res, dict) and "signedUrl" in res:
                return res["signedUrl"]
            elif hasattr(res, "signed_url"):
                return res.signed_url

            return str(res)

        except StorageException as e:
            logger.error(f"❌ Supabase Storage Exception for user {user_id}: {e}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Storage error: {e}"
            )
        except APIError as e:
            logger.error(f"❌ Supabase API error for user {user_id}: {e}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Supabase API error: {e.message}"
            )
        except Exception as e:
            logger.error(f"💥 Unexpected error during image upload for user {user_id}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="An internal server error occurred while uploading the image."
            )


    async def list_user_uploads(self, user_id: str) -> List[str]:
        """
        Lists a user's files using the Admin client (service_role).
        Data isolation is ensured by the path=user_id parameter.
        """
        try:
            files = self.supabase.storage.from_(self.bucket_name).list(path=user_id)

            user_files: List[str] = []

            for file in files:
                file_name = file.get("name")

                if (
                    file_name
                    and file_name != ".emptyFolderPlaceholder"
                    and file.get("id") is not None
                ):
                    user_files.append(f"{user_id}/{file_name}")

            return user_files

        except Exception as e:
            logger.error(f"❌ Admin listing error for user {user_id}: {e}")

            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to list your files.",
            )

