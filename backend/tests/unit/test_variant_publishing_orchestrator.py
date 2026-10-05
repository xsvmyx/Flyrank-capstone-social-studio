from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from repositories.publish_history_repository import PublishHistoryRepository
from repositories.raw_post_repository import RawPostRepository
from repositories.variant_repository import VariantRepository
from schemas.publisher_schemas import PublisherResponse
from schemas.variant_schemas import SocialPlatform, VariantResponse, VariantStatus
from services.publish_service import PublishService
from services.variant_publishing_orchestrator import VariantPublishingOrchestrator


@pytest.fixture
def mock_variant_repo():
    repo = MagicMock(spec=VariantRepository)
    repo.get_by_id = AsyncMock()
    repo.update_status_by_id = AsyncMock()
    return repo


@pytest.fixture
def mock_publish_history_repo():
    repo = MagicMock(spec=PublishHistoryRepository)
    repo.update = AsyncMock()
    return repo


@pytest.fixture
def mock_raw_post_repo():
    repo = MagicMock(spec=RawPostRepository)
    repo.get_image_url_by_id = AsyncMock()
    return repo


@pytest.fixture
def mock_publish_service():
    service = MagicMock(spec=PublishService)
    service.publish_variant = AsyncMock()
    return service


@pytest.fixture
def orchestrator(
    mock_variant_repo, mock_publish_history_repo, mock_raw_post_repo, mock_publish_service
):
    return VariantPublishingOrchestrator(
        variant_repository=mock_variant_repo,
        publish_history_repository=mock_publish_history_repo,
        raw_post_repositroy=mock_raw_post_repo,
        publish_service=mock_publish_service,
    )


# ==========================================
# Tests for execute_job
# ==========================================

@pytest.mark.asyncio
async def test_execute_job_variant_not_found(orchestrator, mock_variant_repo):
    payload = {"variant_id": "var_123", "history_id": "hist_123"}
    mock_variant_repo.get_by_id.return_value = None

    with pytest.raises(ValueError, match="Variant with ID var_123 not found"):
        await orchestrator.execute_job(payload)


@pytest.mark.asyncio
async def test_execute_job_invalid_status_draft(orchestrator, mock_variant_repo, mock_publish_history_repo):
    payload = {"variant_id": "var_123", "history_id": "hist_123"}
    
    variant = MagicMock()
    variant.status = VariantStatus.DRAFT
    mock_variant_repo.get_by_id.return_value = variant

    await orchestrator.execute_job(payload)

    # Should update history to failed and exit gracefully
    mock_publish_history_repo.update.assert_called_once()
    call_args = mock_publish_history_repo.update.call_args[0]
    assert call_args[0] == "hist_123"
    update_data = call_args[1]
    assert update_data.status == "failed"
    assert "must be 'approved' or 'scheduled'" in update_data.error_message


@pytest.mark.asyncio
async def test_execute_job_success(
    orchestrator, mock_variant_repo, mock_raw_post_repo, mock_publish_service, mock_publish_history_repo
):
    payload = {"variant_id": "var_123", "history_id": "hist_123"}
    
    variant = MagicMock()
    variant.status = VariantStatus.APPROVED
    variant.platform = SocialPlatform.DISCORD
    variant.post_id = "post_123"
    mock_variant_repo.get_by_id.return_value = variant
    
    mock_raw_post_repo.get_image_url_by_id.return_value = "https://example.com/image.png"

    pub_response = PublisherResponse(success=True, external_post_id="ext_456", status_code=200, platform=SocialPlatform.DISCORD)
    mock_publish_service.publish_variant.return_value = pub_response
    
    await orchestrator.execute_job(payload)

    mock_publish_service.publish_variant.assert_called_once_with(
        variant=variant, image_url="https://example.com/image.png"
    )

    # Check history update
    mock_publish_history_repo.update.assert_called_once()
    call_args_hist = mock_publish_history_repo.update.call_args[0]
    assert call_args_hist[0] == "hist_123"
    assert call_args_hist[1].status == "success"
    assert call_args_hist[1].response_payload == pub_response.model_dump()

    # Check variant status update
    mock_variant_repo.update_status_by_id.assert_called_once_with(
        variant_id="var_123", status=VariantStatus.PUBLISHED, error_message=None
    )


@pytest.mark.asyncio
async def test_execute_job_publishing_fails(
    orchestrator, mock_variant_repo, mock_publish_service, mock_publish_history_repo
):
    payload = {"variant_id": "var_123", "history_id": "hist_123"}
    
    variant = MagicMock()
    variant.status = VariantStatus.APPROVED
    variant.platform = SocialPlatform.DISCORD
    mock_variant_repo.get_by_id.return_value = variant

    mock_publish_service.publish_variant.side_effect = RuntimeError("Network partition")
    
    with pytest.raises(RuntimeError, match="Network partition"):
        await orchestrator.execute_job(payload)
        
    mock_publish_history_repo.update.assert_called_once()
    call_args_hist = mock_publish_history_repo.update.call_args[0]
    assert call_args_hist[0] == "hist_123"
    assert call_args_hist[1].status == "failed"
    assert "Network partition" in call_args_hist[1].error_message


# ==========================================
# Extra Cases & Internal Methods Tests
# ==========================================

@pytest.mark.asyncio
async def test_execute_job_success_no_history_id(
    orchestrator, mock_variant_repo, mock_raw_post_repo, mock_publish_service, mock_publish_history_repo
):
    payload = {"variant_id": "var_123"}  # No history_id
    
    variant = MagicMock()
    variant.status = VariantStatus.APPROVED
    variant.platform = SocialPlatform.DISCORD
    variant.post_id = "post_123"
    mock_variant_repo.get_by_id.return_value = variant
    
    mock_raw_post_repo.get_image_url_by_id.return_value = None

    pub_response = PublisherResponse(success=True, external_post_id="ext_456", status_code=200, platform=SocialPlatform.DISCORD)
    mock_publish_service.publish_variant.return_value = pub_response
    
    await orchestrator.execute_job(payload)

    # Everything succeeds, but history repo is never called since history_id is not given
    mock_publish_history_repo.update.assert_not_called()
    mock_variant_repo.update_status_by_id.assert_called_once_with(
        variant_id="var_123", status=VariantStatus.PUBLISHED, error_message=None
    )


@pytest.mark.asyncio
async def test_publish_dict_response(orchestrator, mock_publish_service):
    variant = MagicMock()
    variant.platform = SocialPlatform.TWITTER
    
    mock_publish_service.publish_variant.return_value = {"success": True, "external_id": "999"}
    
    res = await orchestrator.publish(variant, image_url=None)
    
    assert res == {"success": True, "external_id": "999"}


@pytest.mark.asyncio
async def test_update_variant_state(orchestrator, mock_variant_repo):
    await orchestrator.update_variant_state(
        variant_id="var_222",
        status=VariantStatus.REJECTED,
        error_message="Too long"
    )
    mock_variant_repo.update_status_by_id.assert_called_once_with(
        variant_id="var_222", status=VariantStatus.REJECTED, error_message="Too long"
    )


@pytest.mark.asyncio
async def test_update_history_state(orchestrator, mock_publish_history_repo):
    await orchestrator.update_history_state(
        history_id="hist_999",
        status="success",
        response_payload={"foo": "bar"},
        error_message=None
    )
    mock_publish_history_repo.update.assert_called_once()
    args = mock_publish_history_repo.update.call_args[0]
    assert args[0] == "hist_999"
    update_data = args[1]
    assert update_data.status == "success"
    assert update_data.response_payload == {"foo": "bar"}
    assert update_data.error_message is None
