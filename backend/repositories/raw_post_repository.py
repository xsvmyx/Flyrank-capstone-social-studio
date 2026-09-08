from config.settings import logger
from typing import List, Optional
from supabase import Client

from schemas.posts_schemas import RawPostCreate, RawPostResponse



class RawPostRepository:
    def __init__(self, supabase_client: Client):
        self.supabase = supabase_client

    async def create(
        self, 
        post_data: RawPostCreate, 
        user_id: str
    ) -> RawPostResponse:
        """Insère un nouveau raw post dans la base de données."""
        payload = {
            "title": post_data.title,
            "raw_content": post_data.raw_content,
            "image_url": post_data.image_url,
            "user_id": user_id,
        }

        response = self.supabase.table("raw_posts").insert(payload).execute()

        if not response.data:
            raise ValueError("Failed to insert raw post into database.")

        return RawPostResponse(**response.data[0])

    async def get_all(self, limit: int = 50, offset: int = 0) -> List[RawPostResponse]:
        response = (
            self.supabase.table("raw_posts")
            .select("*")
            .range(offset, offset + limit - 1)
            .execute()
        )
        return [RawPostResponse(**item) for item in (response.data or [])]

    async def get_by_id(self, post_id: str) -> Optional[RawPostResponse]:
        response = (
            self.supabase.table("raw_posts")
            .select("*")
            .eq("id", post_id)
            .execute()
        )
        if not response.data:
            return None
        return RawPostResponse(**response.data[0])

    async def get_by_title(self, title: str) -> Optional[RawPostResponse]:
        response = (
            self.supabase.table("raw_posts")
            .select("*")
            .eq("title", title)
            .execute()
        )
        if not response.data:
            return None
        return RawPostResponse(**response.data[0])



    # async def get_downloadable_media_url(
    #     self, raw_path: str, bucket_name: str = "post-media"
    # ) -> str:

    #     if raw_path.startswith(("http://", "https://")):
    #         return raw_path

    #     logger.info(f"🔑 Generating signed URL for path: {raw_path}")
    #     res = self.supabase.storage.from_(bucket_name).create_signed_url(raw_path, 3600)

    #     if isinstance(res, dict):
    #         return res.get("signedUrl") or res.get("signed_url", "")
    #     return getattr(res, "signed_url", str(res))