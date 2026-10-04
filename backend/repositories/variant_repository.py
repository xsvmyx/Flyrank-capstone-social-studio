from typing import Dict, List, Optional
from supabase import Client
from schemas.variant_schemas import GeneratedVariant, VariantResponse, VariantStatus
from datetime import datetime


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



    async def create_one(
        self,
        post_id: str,
        variant: GeneratedVariant
    ) -> VariantResponse:
        """
        Inserts or updates a generated content variant for a given post_id.
        Sets status dynamically (DRAFT if valid, REJECTED if invalid)
        and captures validation_error.
        """
        payload = {
            "post_id": post_id,
            "platform": (
                variant.platform.value
                if hasattr(variant.platform, "value")
                else variant.platform
            ),
            "content": variant.content,
            "status": (
                VariantStatus.DRAFT.value
                if variant.is_valid
                else VariantStatus.REJECTED.value
            ),
            "error_message": (
                variant.validation_error
                if not variant.is_valid
                else None
            ),
        }

        response = (
            self.supabase
            .table(self.table_name)
            .upsert(payload, on_conflict="post_id, platform")
            .execute()
        )

        if not response.data:
            raise ValueError("Failed to insert or update variant in database.")

        return VariantResponse(**response.data[0])






    async def update_status_by_id(
        self, 
        variant_id: str, 
        status: VariantStatus,
        error_message: Optional[str] = None,
        scheduled_at: Optional[datetime] = None
    ) -> Optional[VariantResponse]:
        """
        Updates the status (and optionally error_message, scheduled_at) of a single variant by its ID.
        """
        update_payload = {
            "status": status.value if isinstance(status, VariantStatus) else status
        }
        
        if error_message is not None:
            update_payload["error_message"] = error_message

        if scheduled_at is not None:
            update_payload["scheduled_at"] = scheduled_at.isoformat()

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



    async def get_platform_statuses_by_post_id(
        self, post_id: str
    ) -> Dict[str, Dict[str, str | None]]:
        response = (
            self.supabase.table(self.table_name)
            .select("platform, status, error_message")
            .eq("post_id", post_id)
            .execute()
        )

        if not response.data:
            return {}

        return {
            item["platform"]: {
                "status": item["status"],
                "error_message": item["error_message"],
            }
            for item in response.data
        }



