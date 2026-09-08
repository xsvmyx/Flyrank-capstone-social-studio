from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from supabase import Client
from app.database import get_user_db_client
from app.database import supabase_admin
from repositories.raw_post_repository import RawPostRepository
from repositories.storage_repository import StorageRepository
from services.upload_service import UploadService


security = HTTPBearer(auto_error=False)


def validate_token(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
):
    if credentials is None or not credentials.credentials:
        raise HTTPException(
            status_code=401,
            detail="Access token required",
        )

    token = credentials.credentials

    try:
        response = supabase_admin.auth.get_user(token)
        if response is None or getattr(response, "user", None) is None:
            raise HTTPException(
                status_code=401,
                detail="Invalid access token",
            )
        
        return {
            "user": response.user,
            "token": token
        }

    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=401,
            detail="Invalid access token",
        )


def get_db(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
) -> Client:
    """Inject a user-scoped Supabase client based on the provided JWT access token."""
    if credentials is None or not credentials.credentials:
        raise HTTPException(status_code=401, detail="Access token required")

    return get_user_db_client(credentials.credentials)



############ REPOSITORIES



def get_raw_post_repository(db: Client = Depends(get_db)) -> RawPostRepository:
    return RawPostRepository(supabase_client=db)


def get_storage_repository() -> StorageRepository:
    """Uses admin client for bypass storage policies if needed."""
    return StorageRepository(supabase_client=supabase_admin)


############# SERVICES



def get_upload_service(
    storage_repo: StorageRepository = Depends(get_storage_repository)
) -> UploadService:
    """Instantiates UploadService with its StorageRepository dependency."""
    return UploadService(storage_repo=storage_repo)