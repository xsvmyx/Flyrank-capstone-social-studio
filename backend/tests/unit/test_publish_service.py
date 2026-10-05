from unittest.mock import AsyncMock, patch, MagicMock
import pytest
from fastapi import HTTPException

from services.publish_service import PublishService
from schemas.variant_schemas import VariantResponse, VariantStatus, SocialPlatform
from schemas.publish_history_schemas import PublishHistoryCreate, PublishHistoryResponse
from schemas.publisher_schemas import PublisherResponse


@pytest.fixture
def mock_publish_history_repo():
    repo = MagicMock()
    repo.get_by_variant_id = AsyncMock(return_value=[])
    repo.delete_by_variant_id = AsyncMock()
    repo.create = AsyncMock()
    return repo


@pytest.fixture
def mock_variant_repo():
    repo = MagicMock()
    repo.get_by_id = AsyncMock()
    return repo


@pytest.fixture
def mock_discord_publisher():
    pub = MagicMock()
    pub.platform = "discord"
    pub.publish = AsyncMock(return_value=PublisherResponse(platform=SocialPlatform.DISCORD, success=True, external_post_id="123", status_code=200))
    return pub


@pytest.fixture
def publish_service(mock_publish_history_repo, mock_variant_repo, mock_discord_publisher):
    with patch("services.publish_service.PublishService._load_publisher_modules"), \
         patch("services.publish_service.get_registered_publishers") as mock_get_registered:
        
        # Make the service load our mock publisher
        mock_get_registered.return_value = [lambda: mock_discord_publisher]
        service = PublishService(
            publish_history_repo=mock_publish_history_repo,
            variant_repo=mock_variant_repo,
        )
    return service


# ==========================================
# Tests for get_publisher
# ==========================================

def test_get_publisher_success(publish_service, mock_discord_publisher):
    pub = publish_service.get_publisher("discord")
    assert pub == mock_discord_publisher


def test_get_publisher_unsupported(publish_service):
    with pytest.raises(HTTPException) as exc:
        publish_service.get_publisher("unknown")
    assert exc.value.status_code == 400
    assert "Unsupported platform" in exc.value.detail


# ==========================================
# Tests for trigger_publication
# ==========================================

@pytest.mark.asyncio
async def test_trigger_publication_already_success(publish_service, mock_publish_history_repo):
    existing = MagicMock()
    existing.status = "success"
    mock_publish_history_repo.get_by_variant_id.return_value = [existing]

    with pytest.raises(HTTPException) as exc:
        await publish_service.trigger_publication("12345678-1234-5678-1234-567812345678")
        
    assert exc.value.status_code == 409
    assert "already been successfully published" in exc.value.detail


@pytest.mark.asyncio
async def test_trigger_publication_already_pending(publish_service, mock_publish_history_repo):
    existing = MagicMock()
    existing.status = "pending"
    mock_publish_history_repo.get_by_variant_id.return_value = [existing]

    with pytest.raises(HTTPException) as exc:
        await publish_service.trigger_publication("12345678-1234-5678-1234-567812345678")
        
    assert exc.value.status_code == 409
    assert "already pending" in exc.value.detail


@pytest.mark.asyncio
async def test_trigger_publication_variant_not_found(publish_service, mock_variant_repo):
    mock_variant_repo.get_by_id.return_value = None

    with pytest.raises(HTTPException) as exc:
        await publish_service.trigger_publication("12345678-1234-5678-1234-567812345678")
        
    assert exc.value.status_code == 404
    assert "not found" in exc.value.detail


@pytest.mark.asyncio
async def test_trigger_publication_variant_draft(publish_service, mock_variant_repo):
    variant = MagicMock()
    variant.status = VariantStatus.DRAFT
    mock_variant_repo.get_by_id.return_value = variant

    with pytest.raises(HTTPException) as exc:
        await publish_service.trigger_publication("12345678-1234-5678-1234-567812345678")
        
    assert exc.value.status_code == 400
    assert "must be 'approved' or 'scheduled'" in exc.value.detail


@pytest.mark.asyncio
async def test_trigger_publication_success(publish_service, mock_publish_history_repo, mock_variant_repo):
    variant = MagicMock()
    variant.status = VariantStatus.APPROVED
    mock_variant_repo.get_by_id.return_value = variant
    
    new_record = MagicMock()
    new_record.id = "hist_1"
    mock_publish_history_repo.create.return_value = new_record

    result = await publish_service.trigger_publication("12345678-1234-5678-1234-567812345678")
    
    assert result == new_record
    mock_publish_history_repo.create.assert_called_once()
    
    # Check the payload sent to create
    call_args = mock_publish_history_repo.create.call_args[1]
    history_data = call_args["history_data"]
    assert str(history_data.variant_id) == "12345678-1234-5678-1234-567812345678"
    assert history_data.status == "pending"


@pytest.mark.asyncio
async def test_trigger_publication_retry_failed(publish_service, mock_publish_history_repo, mock_variant_repo):
    # Setup previously failed history
    existing = MagicMock()
    existing.status = "failed"
    mock_publish_history_repo.get_by_variant_id.return_value = [existing]
    
    variant = MagicMock()
    variant.status = VariantStatus.APPROVED
    mock_variant_repo.get_by_id.return_value = variant
    
    mock_publish_history_repo.create.return_value = MagicMock()

    await publish_service.trigger_publication("12345678-1234-5678-1234-567812345678")
    
    # Needs to delete the old history before creating new
    mock_publish_history_repo.delete_by_variant_id.assert_called_once_with("12345678-1234-5678-1234-567812345678")
    mock_publish_history_repo.create.assert_called_once()


# ==========================================
# Tests for publish_variant
# ==========================================

@pytest.mark.asyncio
async def test_publish_variant_success(publish_service, mock_discord_publisher):
    variant = MagicMock(spec=VariantResponse)
    variant.id = "var_1"
    variant.platform = SocialPlatform.DISCORD
    variant.content = "Hello Discord!"
    variant.metadata = {"embed": True}
    
    image_url = "https://example.com/img.png"
    
    result = await publish_service.publish_variant(variant, image_url)
    
    assert result.success is True
    mock_discord_publisher.publish.assert_called_once_with(
        content="Hello Discord!",
        metadata={"embed": True},
        image_url=image_url
    )
