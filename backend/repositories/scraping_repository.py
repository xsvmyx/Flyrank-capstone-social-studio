from typing import List, Optional

from supabase import Client
from schemas.scraping_schemas import (
    ScrapingRequestCreate,
    ScrapingRequestResponse,
    ScrapingStatus,
)


class ScrapingRepository:
    def __init__(self, supabase_client: Client):
        self.supabase = supabase_client
        self.table_name = "scraping_requests"

    async def create(
        self,
        request_data: ScrapingRequestCreate,
        user_id: str
    ) -> ScrapingRequestResponse:
        """Insert a new scraping request into the database."""
        payload = {
            "url": str(request_data.url),
            "user_id": user_id,
            "status": ScrapingStatus.PENDING.value,
        }

        response = (
            self.supabase
            .table(self.table_name)
            .insert(payload)
            .execute()
        )

        if not response.data:
            raise ValueError("Failed to insert scraping request into database.")

        return ScrapingRequestResponse(**response.data[0])

    async def get_by_id(
        self,
        request_id: str
    ) -> Optional[ScrapingRequestResponse]:
        """Retrieve a scraping request by its ID."""
        response = (
            self.supabase
            .table(self.table_name)
            .select("*")
            .eq("id", request_id)
            .execute()
        )

        if not response.data:
            return None

        return ScrapingRequestResponse(**response.data[0])

    async def get_by_user_id(
        self,
        user_id: str,
        limit: int = 50,
        offset: int = 0
    ) -> List[ScrapingRequestResponse]:
        """Retrieve the scraping request history for a user."""
        response = (
            self.supabase
            .table(self.table_name)
            .select("*")
            .eq("user_id", user_id)
            .order("created_at", desc=True)
            .range(offset, offset + limit - 1)
            .execute()
        )

        return [
            ScrapingRequestResponse(**item)
            for item in (response.data or [])
        ]

    async def update_status(
        self,
        request_id: str,
        status: ScrapingStatus,
        error_message: Optional[str] = None
    ) -> ScrapingRequestResponse:
        """Update the status and optional error message of a scraping request."""
        payload = {
            "status": status.value if hasattr(status, "value") else str(status),
            "error_message": error_message,
        }

        response = (
            self.supabase
            .table(self.table_name)
            .update(payload)
            .eq("id", request_id)
            .execute()
        )

        if not response.data:
            raise ValueError(
                f"Failed to update scraping request {request_id}."
            )

        return ScrapingRequestResponse(**response.data[0])