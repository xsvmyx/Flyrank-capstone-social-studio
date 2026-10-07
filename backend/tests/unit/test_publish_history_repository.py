import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4
from datetime import datetime, timezone
from schemas.publish_history_schemas import PublishHistoryResponse
from repositories.publish_history_repository import PublishHistoryRepository


@pytest.fixture
def mock_supabase():
    client = MagicMock()
    return client


@pytest.fixture
def repo(mock_supabase):
    return PublishHistoryRepository(supabase_client=mock_supabase)


@pytest.mark.asyncio
async def test_get_by_variant_id(repo, mock_supabase):
    sample_id = uuid4()
    mock_supabase.table.return_value.select.return_value.eq.return_value.order.return_value.execute.return_value = MagicMock(
        data=[
            {
                "id": str(uuid4()),
                "variant_id": str(sample_id),
                "idempotency_key": "key-1",
                "status": "success",
                "response_payload": {"id": "ext-1"},
                "error_message": None,
                "attempt_count": 1,
                "executed_at": datetime.now(timezone.utc).isoformat(),
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
        ]
    )

    results = await repo.get_by_variant_id(sample_id)
    assert len(results) == 1
    assert isinstance(results[0], PublishHistoryResponse)
    assert results[0].status == "success"


@pytest.mark.asyncio
async def test_get_all_pagination(repo, mock_supabase):
    mock_supabase.table.return_value.select.return_value.order.return_value.range.return_value.execute.return_value = MagicMock(
        data=[
            {
                "id": str(uuid4()),
                "variant_id": str(uuid4()),
                "idempotency_key": "key-2",
                "status": "pending",
                "response_payload": {},
                "error_message": None,
                "attempt_count": 1,
                "executed_at": datetime.now(timezone.utc).isoformat(),
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
        ]
    )

    results = await repo.get_all(limit=10, offset=0)
    assert len(results) == 1
    assert results[0].idempotency_key == "key-2"
