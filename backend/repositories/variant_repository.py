from typing import List, Optional
from supabase import Client
from schemas.variant_schemas import GeneratedVariant, VariantResponse, VariantStatus


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
        Batch inserts/upserts a list of generated content variants for a given post_id.
        Sets status dynamically (DRAFT if valid, REJECTED if invalid) and captures validation_error.
        """
        if not variants:
            return []

        payload = [
            {
                "post_id": post_id,
                "platform": variant.platform.value if hasattr(variant.platform, "value") else variant.platform,
                "content": variant.content,
                "status": VariantStatus.DRAFT.value if variant.is_valid else VariantStatus.REJECTED.value,
                "error_message": variant.validation_error if not variant.is_valid else None,
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

    async def update_status_by_id(
        self, 
        variant_id: str, 
        status: VariantStatus,
        error_message: Optional[str] = None
    ) -> Optional[VariantResponse]:
        """
        Updates the status (and optionally error_message) of a single variant by its ID.
        """
        update_payload = {
            "status": status.value if isinstance(status, VariantStatus) else status
        }
        if error_message is not None:
            update_payload["error_message"] = error_message

        response = (
            self.supabase.table(self.table_name)
            .update(update_payload)
            .eq("id", variant_id)
            .execute()
        )

        if not response.data:
            return None

        return VariantResponse(**response.data[0])

    async def update_status_by_post_id(
        self, 
        post_id: str, 
        status: VariantStatus,
        error_message: Optional[str] = None
    ) -> List[VariantResponse]:
        """
        Bulk updates the status (and optionally error_message) for all variants belonging to a post_id.
        """
        update_payload = {
            "status": status.value if isinstance(status, VariantStatus) else status
        }
        if error_message is not None:
            update_payload["error_message"] = error_message

        response = (
            self.supabase.table(self.table_name)
            .update(update_payload)
            .eq("post_id", post_id)
            .execute()
        )

        return [VariantResponse(**item) for item in (response.data or [])]

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