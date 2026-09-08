from typing import List, Optional
from supabase import Client
from schemas.variant_schemas import GeneratedVariant, VariantResponse


class VariantRepository:
    """
    Repository responsible for data access operations on the public.variants table in Supabase.
    """

    def __init__(self, supabase_client: Client):
        self.supabase = supabase_client
        self.table_name = "variants"

    async def create_many(
        self, 
        post_id: str, 
        variants: List[GeneratedVariant]
    ) -> List[VariantResponse]:
        """
        Batch inserts a list of generated content variants for a given post_id.
        Uses upsert to handle the UNIQUE(post_id, platform) constraint safely.
        """
        if not variants:
            return []

        payload = [
            {
                "post_id": post_id,
                "platform": variant.platform,
                "content": variant.content,
                "status": "completed",
            }
            for variant in variants
        ]

        response = (
            self.supabase.table(self.table_name)
            .upsert(payload, on_conflict="post_id, platform")
            .execute()
        )

        if not response.data:
            raise ValueError("Failed to insert or update variants in database.")

        return [VariantResponse(**item) for item in response.data]

    async def get_by_post_id(self, post_id: str) -> List[VariantResponse]:
        """Retrieves all generated variants associated with a specific raw post."""
        response = (
            self.supabase.table(self.table_name)
            .select("*")
            .eq("post_id", post_id)
            .execute()
        )
        return [VariantResponse(**item) for item in (response.data or [])]

    async def get_by_id(self, variant_id: str) -> Optional[VariantResponse]:
        """Retrieves a single variant by its primary UUID."""
        response = (
            self.supabase.table(self.table_name)
            .select("*")
            .eq("id", variant_id)
            .execute()
        )
        if not response.data:
            return None
        return VariantResponse(**response.data[0])

    async def update_status(
        self, 
        variant_id: str, 
        status: str, 
        error_message: Optional[str] = None
    ) -> Optional[VariantResponse]:
        """Updates the status and optional error message of a specific variant."""
        payload = {"status": status}
        if error_message is not None:
            payload["error_message"] = error_message

        response = (
            self.supabase.table(self.table_name)
            .update(payload)
            .eq("id", variant_id)
            .execute()
        )
        if not response.data:
            return None
        return VariantResponse(**response.data[0])