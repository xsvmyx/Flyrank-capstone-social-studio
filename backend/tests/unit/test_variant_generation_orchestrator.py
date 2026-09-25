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
    service.generate_variants = AsyncMock(return_value=[])
    service.regenerate_variants = AsyncMock(return_value=[])
    return service


@pytest.fixture
def mock_variant_repo():
    repo = MagicMock(spec=VariantRepository)
    repo.get_by_post_id = AsyncMock(return_value=[])
    repo.create_many = AsyncMock(return_value=[])
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
    )


# ==========================================
# 1. Tests for execute_job & validation
# ==========================================

@pytest.mark.asyncio
async def test_execute_job_missing_post_id(orchestrator):
    payload = {"user_id": "usr_123"}
    with pytest.raises(ValueError, match="Payload missing required key 'post_id'"):
        await orchestrator.execute_job(payload)


@pytest.mark.asyncio
async def test_execute_job_raw_post_not_found(orchestrator, mock_raw_post_repo):
    mock_raw_post_repo.get_by_id.return_value = None

    with pytest.raises(ValueError, match="Raw post with ID post_404 does not exist."):
        await orchestrator.execute_job({"post_id": "post_404"})


@pytest.mark.asyncio
async def test_execute_job_empty_raw_content(orchestrator, mock_raw_post_repo, sample_raw_post):
    sample_raw_post.raw_content = "   \n  "
    mock_raw_post_repo.get_by_id.return_value = sample_raw_post

    result = await orchestrator.execute_job({"post_id": "post_123"})

    assert result == {
        "status": "skipped",
        "reason": "empty_content",
        "post_id": "post_123",
    }


# ==========================================
# 2. Tests for Full Execution Paths (Initial, Regeneration, Skip)
# ==========================================

@pytest.mark.asyncio
async def test_execute_job_initial_generation_success(
    orchestrator, mock_raw_post_repo, mock_llm_service, mock_variant_repo, sample_raw_post
):
    mock_raw_post_repo.get_by_id.return_value = sample_raw_post
    mock_variant_repo.get_by_post_id.return_value = []  # Initial run: no existing variants

    generated_variants = [
        GeneratedVariant(
            platform=SocialPlatform.TWITTER,
            content="Tweet about AI revolution!",
            hashtags=["#AI"],
        ),
        GeneratedVariant(
            platform=SocialPlatform.LINKEDIN,
            content="In-depth post about AI...",
            hashtags=["#Tech"],
        ),
    ]
    mock_llm_service.generate_variants.return_value = generated_variants

    persisted_variants = [
        VariantResponse(
            id="var_1",
            post_id="post_123",
            platform=SocialPlatform.TWITTER,
            content="Tweet about AI revolution!",
            status=VariantStatus.DRAFT,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        ),
        VariantResponse(
            id="var_2",
            post_id="post_123",
            platform=SocialPlatform.LINKEDIN,
            content="In-depth post about AI...",
            status=VariantStatus.DRAFT,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        ),
    ]
    mock_variant_repo.create_many.return_value = persisted_variants

    result = await orchestrator.execute_job({"post_id": "post_123"})

    assert result == {
        "status": "success",
        "post_id": "post_123",
        "generated_count": 2,
    }

    mock_llm_service.generate_variants.assert_called_once_with(
        source_text="Artificial Intelligence is advancing rapidly..."
    )
    mock_variant_repo.create_many.assert_called_once_with(
        post_id="post_123",
        variants=generated_variants,
    )


@pytest.mark.asyncio
async def test_execute_job_targeted_regeneration_for_rejected_variants(
    orchestrator, mock_raw_post_repo, mock_llm_service, mock_variant_repo, sample_raw_post
):
    mock_raw_post_repo.get_by_id.return_value = sample_raw_post

    # DB contains Twitter (REJECTED) and LinkedIn (APPROVED)
    existing_variants = [
        VariantResponse(
            id="v1",
            post_id="post_123",
            platform=SocialPlatform.TWITTER,
            content="Old tweet",
            status=VariantStatus.REJECTED,
            error_message="Too long, keep under 280 chars.",
            created_at=datetime.now(),
            updated_at=datetime.now(),
        ),
        VariantResponse(
            id="v2",
            post_id="post_123",
            platform=SocialPlatform.LINKEDIN,
            content="Approved LinkedIn post",
            status=VariantStatus.APPROVED,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        ),
    ]
    mock_variant_repo.get_by_post_id.return_value = existing_variants

    regenerated_variant = GeneratedVariant(
        platform=SocialPlatform.TWITTER,
        content="Fixed short tweet",
        hashtags=["#AI"],
    )
    mock_llm_service.regenerate_variants.return_value = [regenerated_variant]
    mock_variant_repo.create_many.return_value = [
        VariantResponse(
            id="v3",
            post_id="post_123",
            platform=SocialPlatform.TWITTER,
            content="Fixed short tweet",
            status=VariantStatus.DRAFT,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
    ]

    result = await orchestrator.execute_job({"post_id": "post_123"})

    assert result == {
        "status": "success",
        "post_id": "post_123",
        "generated_count": 1,
    }

    mock_llm_service.regenerate_variants.assert_called_once_with(
        source_text="Artificial Intelligence is advancing rapidly...",
        target_feedbacks={"twitter": "Too long, keep under 280 chars."},
    )


@pytest.mark.asyncio
async def test_execute_job_draft_only_skipped(
    orchestrator, mock_raw_post_repo, mock_variant_repo, sample_raw_post
):
    mock_raw_post_repo.get_by_id.return_value = sample_raw_post
    existing_variants = [
        VariantResponse(
            id="v1",
            post_id="post_123",
            platform=SocialPlatform.TWITTER,
            status=VariantStatus.DRAFT,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
    ]
    mock_variant_repo.get_by_post_id.return_value = existing_variants

    result = await orchestrator.execute_job({"post_id": "post_123"})

    assert result == {
        "status": "skipped",
        "reason": "nothing_to_generate",
        "post_id": "post_123",
    }


@pytest.mark.asyncio
async def test_execute_job_approved_only_skipped(
    orchestrator, mock_raw_post_repo, mock_variant_repo, sample_raw_post
):
    mock_raw_post_repo.get_by_id.return_value = sample_raw_post
    existing_variants = [
        VariantResponse(
            id="v1",
            post_id="post_123",
            platform=SocialPlatform.TWITTER,
            status=VariantStatus.APPROVED,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
    ]
    mock_variant_repo.get_by_post_id.return_value = existing_variants

    result = await orchestrator.execute_job({"post_id": "post_123"})

    assert result == {
        "status": "skipped",
        "reason": "nothing_to_generate",
        "post_id": "post_123",
    }


@pytest.mark.asyncio
async def test_execute_job_fatal_error(orchestrator, mock_raw_post_repo):
    mock_raw_post_repo.get_by_id.side_effect = RuntimeError("Database connection lost")

    with pytest.raises(RuntimeError, match="Database connection lost"):
        await orchestrator.execute_job({"post_id": "post_123"})


# ==========================================
# 3. Tests for _get_categorized_platforms
# ==========================================

@pytest.mark.asyncio
async def test_get_categorized_platforms_empty(orchestrator, mock_variant_repo):
    mock_variant_repo.get_by_post_id.return_value = []

    approved, rejected, draft = await orchestrator._get_categorized_platforms("post_123")

    assert approved == {}
    assert rejected == {}
    assert draft == {}


@pytest.mark.asyncio
async def test_get_categorized_platforms_mixed(orchestrator, mock_variant_repo):
    variants = [
        VariantResponse(
            id="v1",
            post_id="p1",
            platform=SocialPlatform.LINKEDIN,
            status=VariantStatus.APPROVED,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        ),
        VariantResponse(
            id="v2",
            post_id="p1",
            platform=SocialPlatform.TWITTER,
            status=VariantStatus.REJECTED,
            error_message="Too long",
            created_at=datetime.now(),
            updated_at=datetime.now(),
        ),
        VariantResponse(
            id="v3",
            post_id="p1",
            platform=SocialPlatform.INSTAGRAM,
            status=VariantStatus.DRAFT,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        ),
    ]
    mock_variant_repo.get_by_post_id.return_value = variants

    approved, rejected, draft = await orchestrator._get_categorized_platforms("p1")

    assert approved == {"linkedin": None}
    assert rejected == {"twitter": "Too long"}
    assert draft == {"instagram": None}


# ==========================================
# 4. Tests for _generate_text_variants & _persist_results
# ==========================================

@pytest.mark.asyncio
async def test_generate_text_variants_pipeline_exception(orchestrator, mock_llm_service):
    mock_llm_service.generate_variants.side_effect = Exception("LLM crash")

    # Should catch exception internally and return empty list []
    result = await orchestrator._generate_text_variants("Source text")

    assert result == []


@pytest.mark.asyncio
async def test_persist_results_empty(orchestrator, mock_variant_repo):
    results = await orchestrator._persist_results("post_123", [])

    assert results == []
    mock_variant_repo.create_many.assert_not_called()


@pytest.mark.asyncio
async def test_persist_results_database_error(orchestrator, mock_variant_repo):
    mock_variant_repo.create_many.side_effect = RuntimeError("DB write error")

    variant = GeneratedVariant(platform=SocialPlatform.TWITTER, content="Text")

    with pytest.raises(RuntimeError, match="DB write error"):
        await orchestrator._persist_results("post_123", [variant])
