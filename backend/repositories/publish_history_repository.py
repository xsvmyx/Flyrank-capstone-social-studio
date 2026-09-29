from typing import List, Optional
from uuid import UUID
from supabase import Client

from schemas.publish_history_schemas import (
    PublishHistoryCreate,
    PublishHistoryResponse,
    PublishHistoryUpdate,
)


class PublishHistoryRepository:
    def __init__(self, supabase_client: Client):
        self.supabase = supabase_client
        self.table_name = "publish_history"

    async def create(
        self, history_data: PublishHistoryCreate
    ) -> PublishHistoryResponse:
        payload = {
            "variant_id": str(history_data.variant_id),
            "idempotency_key": history_data.idempotency_key,
            "status": history_data.status,
            "response_payload": history_data.response_payload or {},
            "error_message": history_data.error_message,
            "attempt_count": history_data.attempt_count,
        }

        response = self.supabase.table(self.table_name).insert(payload).execute()

        if not response.data:
            raise ValueError("Failed to insert publish history record into database.")

        return PublishHistoryResponse(**response.data[0])

    async def get_by_id(self, history_id: str | UUID) -> Optional[PublishHistoryResponse]:
        response = (
            self.supabase.table(self.table_name)
            .select("*")
            .eq("id", str(history_id))
            .execute()
        )
        if not response.data:
            return None
        return PublishHistoryResponse(**response.data[0])

    async def get_by_idempotency_key(
        self, idempotency_key: str
    ) -> Optional[PublishHistoryResponse]:
        response = (
            self.supabase.table(self.table_name)
            .select("*")
            .eq("idempotency_key", idempotency_key)
            .execute()
        )
        if not response.data:
            return None
        return PublishHistoryResponse(**response.data[0])

    async def get_by_variant_id(
        self, variant_id: str | UUID
    ) -> List[PublishHistoryResponse]:
        response = (
            self.supabase.table(self.table_name)
            .select("*")
            .eq("variant_id", str(variant_id))
            .order("created_at", desc=True)
            .execute()
        )
        return [PublishHistoryResponse(**item) for item in (response.data or [])]

    async def update(
        self, history_id: str | UUID, update_data: PublishHistoryUpdate
    ) -> PublishHistoryResponse:
        payload = {
            k: v
            for k, v in update_data.model_dump(exclude_unset=True).items()
            if v is not None
        }

        if "executed_at" in payload and payload["executed_at"]:
            payload["executed_at"] = payload["executed_at"].isoformat()

        response = (
            self.supabase.table(self.table_name)
            .update(payload)
            .eq("id", str(history_id))
            .execute()
        )

        if not response.data:
            raise ValueError(f"Failed to update publish history record: {history_id}")

        return PublishHistoryResponse(**response.data[0])

    async def delete_by_variant_id(self, variant_id: str | UUID) -> List[PublishHistoryResponse]:
        """
        Deletes all publish history records associated with a given variant_id.
        Returns the deleted records.
        """
        response = (
            self.supabase.table(self.table_name)
            .delete()
            .eq("variant_id", str(variant_id))
            .execute()
        )

        return [PublishHistoryResponse(**item) for item in (response.data or [])]