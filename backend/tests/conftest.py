import os
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

# Set dummy environment variables BEFORE any application module imports
os.environ.setdefault("SUPABASE_URL", "https://dummy.supabase.co")
os.environ.setdefault("SUPABASE_ANON_KEY", "dummy-anon-key")
os.environ.setdefault("SUPABASE_SERVICE_KEY", "dummy-service-key")
os.environ.setdefault("GROQ_API_KEY", "gsk_dummy_key_for_testing")

from repositories.raw_post_repository import RawPostRepository
from repositories.scraping_repository import ScrapingRepository
from repositories.storage_repository import StorageRepository
from repositories.variant_repository import VariantRepository
from schemas.posts_schemas import RawPostResponse
from schemas.variant_schemas import (
    GeneratedVariant,
    SocialPlatform,
    VariantResponse,
    VariantStatus,
)


# ==========================================
# 1. Shared Data Fixtures
# ==========================================

@pytest.fixture
def sample_user_id() -> str:
    return "usr_test_123"


@pytest.fixture
def sample_post_id() -> str:
    return "post_test_456"


@pytest.fixture
def sample_raw_post(sample_post_id, sample_user_id) -> RawPostResponse:
    return RawPostResponse(
        id=sample_post_id,
        title="Test Article Title",
        raw_content="This is the raw content of the article for testing purposes.",
        image_url="https://example.com/cover.jpg",
        user_id=sample_user_id,
        created_at=datetime.fromisoformat("2026-09-25T12:00:00"),
    )


@pytest.fixture
def sample_generated_variant() -> GeneratedVariant:
    return GeneratedVariant(
        platform=SocialPlatform.TWITTER,
        content="Exciting updates on AI! Check it out #AI #Tech",
        hashtags=["#AI", "#Tech"],
        is_valid=True,
    )


# ==========================================
# 2. Shared Repository Mocks
# ==========================================

@pytest.fixture
def shared_mock_scraping_repo():
    repo = MagicMock(spec=ScrapingRepository)
    repo.update_status = AsyncMock()
    return repo


@pytest.fixture
def shared_mock_raw_post_repo(sample_raw_post):
    repo = MagicMock(spec=RawPostRepository)
    repo.get_by_id = AsyncMock(return_value=sample_raw_post)
    repo.create = AsyncMock(return_value=sample_raw_post)
    return repo


@pytest.fixture
def shared_mock_variant_repo():
    repo = MagicMock(spec=VariantRepository)
    repo.get_by_post_id = AsyncMock(return_value=[])
    repo.create_many = AsyncMock(return_value=[])
    return repo


@pytest.fixture
def shared_mock_storage_repo():
    repo = MagicMock(spec=StorageRepository)
    repo.upload_file = AsyncMock()
    repo.get_signed_url = AsyncMock(return_value="https://storage.example.com/signed/photo.png")
    repo.list_files = AsyncMock(return_value=[])
    return repo
