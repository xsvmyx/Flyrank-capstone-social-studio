from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from supabase import Client
from config.connections import get_user_db_client,supabase_admin
from repositories.raw_post_repository import RawPostRepository
from repositories.storage_repository import StorageRepository
from repositories.variant_repository import VariantRepository
from services.upload_service import UploadService
from services.orchestrator import Orchestrator
from services.llm_service import LLMService

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

def get_variant_repository(db: Client = Depends(get_db)) -> VariantRepository:
    return VariantRepository(supabase_client=db)
1
############# SERVICES



def get_upload_service(
    storage_repo: StorageRepository = Depends(get_storage_repository)
) -> UploadService:
    """Instantiates UploadService with its StorageRepository dependency."""
    return UploadService(storage_repo=storage_repo)






def create_orchestrator() -> Orchestrator:
    
    raw_post_repo = RawPostRepository(supabase_client=supabase_admin)
    variant_repo = VariantRepository(supabase_client=supabase_admin)


    llm_service = LLMService()

    return Orchestrator(
        raw_post_repo=raw_post_repo,
        llm_service=llm_service,
        variant_repo=variant_repo

    )