from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from schemas.variant_schemas import GeneratedVariant, SocialPlatform
from services.agents.base_agent import BaseAgent
from services.llm_service import LLMService


@pytest.fixture
def mock_agent_twitter():
    agent = MagicMock(spec=BaseAgent)
    agent.platform_name = "twitter"
    variant = GeneratedVariant(
        platform=SocialPlatform.TWITTER,
        content="Tweet content #AI",
        hashtags=["#AI"],
        is_valid=True,
    )
    agent.generate_variant = AsyncMock(return_value=variant)
    agent.regenerate_variant = AsyncMock(return_value=variant)
    return agent


@pytest.fixture
def mock_agent_linkedin():
    agent = MagicMock(spec=BaseAgent)
    agent.platform_name = "linkedin"
    variant = GeneratedVariant(
        platform=SocialPlatform.LINKEDIN,
        content="LinkedIn professional post content...",
        hashtags=["#Tech"],
        is_valid=True,
    )
    agent.generate_variant = AsyncMock(return_value=variant)
    agent.regenerate_variant = AsyncMock(return_value=variant)
    return agent


@pytest.fixture
def llm_service(mock_agent_twitter, mock_agent_linkedin):
    with patch("services.llm_service.LLMService._load_agent_modules"), \
         patch("services.llm_service.LLMService._instantiate_agents", return_value=[mock_agent_twitter, mock_agent_linkedin]):
        service = LLMService()
    return service


# ==========================================
# 1. Tests for Service Initialization
# ==========================================

def test_llm_service_initialization(mock_agent_twitter, mock_agent_linkedin):
    with patch("services.llm_service.LLMService._load_agent_modules") as mock_load, \
         patch("services.llm_service.get_registered_agents") as mock_get_registered:
        
        mock_get_registered.return_value = [
            lambda: mock_agent_twitter,
            lambda: mock_agent_linkedin,
        ]
        service = LLMService()

        mock_load.assert_called_once()
        assert len(service._agents) == 2
        assert service._agents[0].platform_name == "twitter"
        assert service._agents[1].platform_name == "linkedin"


# ==========================================
# 2. Tests for generate_variants
# ==========================================

@pytest.mark.asyncio
async def test_generate_variants_no_agents(llm_service):
    llm_service._agents = []
    results = await llm_service.generate_variants("Source text for article")
    assert results == []


@pytest.mark.asyncio
async def test_generate_variants_success(llm_service, mock_agent_twitter, mock_agent_linkedin):
    results = await llm_service.generate_variants("AI is transforming software engineering.")

    assert len(results) == 2
    mock_agent_twitter.generate_variant.assert_called_once_with("AI is transforming software engineering.")
    mock_agent_linkedin.generate_variant.assert_called_once_with("AI is transforming software engineering.")
    
    platforms = [r.platform for r in results]
    assert SocialPlatform.TWITTER in platforms
    assert SocialPlatform.LINKEDIN in platforms


@pytest.mark.asyncio
async def test_generate_variants_with_one_failing_agent(llm_service, mock_agent_twitter, mock_agent_linkedin):
    mock_agent_twitter.generate_variant.side_effect = RuntimeError("Groq Rate Limit Exceeded")

    results = await llm_service.generate_variants("Source content")

    # Should not crash, and should return the valid LinkedIn variant
    assert len(results) == 1
    assert results[0].platform == SocialPlatform.LINKEDIN
    assert results[0].content == "LinkedIn professional post content..."


# ==========================================
# 3. Tests for regenerate_variants
# ==========================================

@pytest.mark.asyncio
async def test_regenerate_variants_no_agents(llm_service):
    llm_service._agents = []
    results = await llm_service.regenerate_variants("Source text", {"twitter": "Too long"})
    assert results == []


@pytest.mark.asyncio
async def test_regenerate_variants_no_matching_targets(llm_service, mock_agent_twitter, mock_agent_linkedin):
    # Registered agents are twitter and linkedin, but target is facebook
    results = await llm_service.regenerate_variants("Source text", {"facebook": "Add more emojis"})

    assert results == []
    mock_agent_twitter.regenerate_variant.assert_not_called()
    mock_agent_linkedin.regenerate_variant.assert_not_called()


@pytest.mark.asyncio
async def test_regenerate_variants_targeted(llm_service, mock_agent_twitter, mock_agent_linkedin):
    # Only target twitter (case insensitive check: 'TWITTER')
    target_feedbacks = {
        "TWITTER": "Please remove tone, keep under 280 chars.",
    }

    results = await llm_service.regenerate_variants("Source text", target_feedbacks)

    assert len(results) == 1
    assert results[0].platform == SocialPlatform.TWITTER
    
    mock_agent_twitter.regenerate_variant.assert_called_once_with(
        source_text="Source text",
        error_message="Please remove tone, keep under 280 chars.",
    )
    mock_agent_linkedin.regenerate_variant.assert_not_called()


@pytest.mark.asyncio
async def test_regenerate_variants_with_failing_agent(llm_service, mock_agent_twitter):
    mock_agent_twitter.regenerate_variant.side_effect = Exception("API Connection lost")

    results = await llm_service.regenerate_variants("Source text", {"twitter": "Fix hashtags"})

    assert results == []
