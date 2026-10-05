from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from repositories.raw_post_repository import RawPostRepository
from repositories.variant_repository import VariantRepository
from schemas.posts_schemas import RawPostResponse
from schemas.variant_schemas import (
    GeneratedVariant,
    SocialPlatform,
    VariantResponse,
    VariantStatus,
)
from services.llm_service import LLMService
from services.variant_generation_orchestrator import VariantGenerationOrchestrator


@pytest.fixture
def mock_raw_post_repo():
    repo = MagicMock(spec=RawPostRepository)
    repo.get_by_id = AsyncMock()
    return repo


@pytest.fixture
def mock_llm_service():
    service = MagicMock(spec=LLMService)
    service.generate_variant_for_platform = AsyncMock()
    return service


@pytest.fixture
def mock_variant_repo():
    repo = MagicMock(spec=VariantRepository)
    repo.get_platform_statuses_by_post_id = AsyncMock(return_value={})
    repo.create_one = AsyncMock()
    return repo


@pytest.fixture
def orchestrator(mock_raw_post_repo, mock_llm_service, mock_variant_repo):
    return VariantGenerationOrchestrator(
        raw_post_repo=mock_raw_post_repo,
        llm_service=mock_llm_service,
        variant_repo=mock_variant_repo,
    )


@pytest.fixture
def sample_raw_post():
    return RawPostResponse(
        id="post_123",
        title="AI Revolution in 2026",
        raw_content="Artificial Intelligence is advancing rapidly...",
        image_url="https://example.com/ai.jpg",
        user_id="usr_555",
        created_at=datetime.fromisoformat("2026-09-25T12:00:00"),
        updated_at=datetime.fromisoformat("2026-09-25T12:00:00"),
    )


# ==========================================
# 1. Tests for execute_job parameter validation
# ==========================================

@pytest.mark.asyncio
async def test_execute_job_missing_post_id(orchestrator):
    payload = {"platform": "twitter"}
    with pytest.raises(ValueError, match="Job payload must contain 'post_id' and 'platform'"):
        await orchestrator.execute_job(payload)


@pytest.mark.asyncio
async def test_execute_job_missing_platform(orchestrator):
    payload = {"post_id": "post_123"}
    with pytest.raises(ValueError, match="Job payload must contain 'post_id' and 'platform'"):
        await orchestrator.execute_job(payload)


# ==========================================
# 2. Tests for _check_generation_needed
# ==========================================

@pytest.mark.asyncio
async def test_check_generation_needed_no_existing(orchestrator):
    statuses = {}
    should_gen, err = await orchestrator._check_generation_needed("twitter", statuses)
    assert should_gen is True
    assert err is None


@pytest.mark.asyncio
async def test_check_generation_needed_draft(orchestrator):
    statuses = {"twitter": {"status": VariantStatus.DRAFT, "error_message": None}}
    should_gen, err = await orchestrator._check_generation_needed("twitter", statuses)
    assert should_gen is False


@pytest.mark.asyncio
async def test_check_generation_needed_approved(orchestrator):
    statuses = {"twitter": {"status": VariantStatus.APPROVED, "error_message": None}}
    should_gen, err = await orchestrator._check_generation_needed("twitter", statuses)
    assert should_gen is False


@pytest.mark.asyncio
async def test_check_generation_needed_published(orchestrator):
    statuses = {"twitter": {"status": VariantStatus.PUBLISHED, "error_message": None}}
    should_gen, err = await orchestrator._check_generation_needed("twitter", statuses)
    assert should_gen is False


@pytest.mark.asyncio
async def test_check_generation_needed_rejected(orchestrator):
    statuses = {"twitter": {"status": VariantStatus.REJECTED, "error_message": "Too long"}}
    should_gen, err = await orchestrator._check_generation_needed("twitter", statuses)
    assert should_gen is True
    assert err == "Too long"


# ==========================================
# 3. Tests for execute_job full paths
# ==========================================

@pytest.mark.asyncio
async def test_execute_job_skipped_due_to_status(orchestrator, mock_variant_repo):
    # Setup: Platform already has a draft variant
    payload = {"post_id": "post_123", "platform": "twitter"}
    mock_variant_repo.get_platform_statuses_by_post_id.return_value = {
        "twitter": {"status": VariantStatus.DRAFT, "error_message": None}
    }
    
    result = await orchestrator.execute_job(payload)
    
    assert result["status"] == "skipped"
    assert "already processed/blocked." in result["reason"]


@pytest.mark.asyncio
async def test_execute_job_raw_post_not_found(orchestrator, mock_variant_repo, mock_raw_post_repo):
    payload = {"post_id": "post_404", "platform": "twitter"}
    mock_variant_repo.get_platform_statuses_by_post_id.return_value = {}
    mock_raw_post_repo.get_by_id.return_value = None

    with pytest.raises(ValueError, match="Raw post with ID post_404 does not exist."):
        await orchestrator.execute_job(payload)


@pytest.mark.asyncio
async def test_execute_job_success(
    orchestrator, mock_variant_repo, mock_raw_post_repo, mock_llm_service, sample_raw_post
):
    payload = {"post_id": "post_123", "platform": "linkedin"}
    
    # 1. Status fetch shows no existing variant
    mock_variant_repo.get_platform_statuses_by_post_id.return_value = {}
    
    # 2. Raw post fetch succeeds
    mock_raw_post_repo.get_by_id.return_value = sample_raw_post
    
    # 3. LLM Generation
    generated = GeneratedVariant(
        platform=SocialPlatform.LINKEDIN,
        content="Professional AI post",
        hashtags=["#AI"],
        is_valid=True
    )
    mock_llm_service.generate_variant_for_platform.return_value = generated
    
    # 4. Persistence
    persisted = VariantResponse(
        id="var_1",
        post_id="post_123",
        platform=SocialPlatform.LINKEDIN,
        content="Professional AI post",
        status=VariantStatus.DRAFT,
        created_at=datetime.now(),
        updated_at=datetime.now()
    )
    mock_variant_repo.create_one.return_value = persisted
    
    result = await orchestrator.execute_job(payload)
    
    assert result["status"] == "success"
    assert result["platform"] == "linkedin"
    assert result["generated_variant"] == persisted
    
    mock_llm_service.generate_variant_for_platform.assert_called_once_with(
        source_text="Artificial Intelligence is advancing rapidly...",
        platform="linkedin",
        error_message=None
    )


@pytest.mark.asyncio
async def test_execute_job_retry_rejected(
    orchestrator, mock_variant_repo, mock_raw_post_repo, mock_llm_service, sample_raw_post
):
    payload = {"post_id": "post_123", "platform": "twitter"}
    
    # 1. Indicates rejected variant exists
    mock_variant_repo.get_platform_statuses_by_post_id.return_value = {
        "twitter": {"status": VariantStatus.REJECTED, "error_message": "Character limit exceeded"}
    }
    
    mock_raw_post_repo.get_by_id.return_value = sample_raw_post
    
    generated = GeneratedVariant(
        platform=SocialPlatform.TWITTER,
        content="Shortened tweet",
        is_valid=True
    )
    mock_llm_service.generate_variant_for_platform.return_value = generated
    mock_variant_repo.create_one.return_value = MagicMock()
    
    await orchestrator.execute_job(payload)
    
    # ensure generate_variant_for_platform got the error message
    mock_llm_service.generate_variant_for_platform.assert_called_once_with(
        source_text="Artificial Intelligence is advancing rapidly...",
        platform="twitter",
        error_message="Character limit exceeded"
    )
