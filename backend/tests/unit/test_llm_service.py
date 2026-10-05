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
# 2. Tests for generate_variant_for_platform
# ==========================================

@pytest.mark.asyncio
async def test_generate_variant_for_platform_no_agents(llm_service):
    llm_service._agents = []
    result = await llm_service.generate_variant_for_platform("Source text", SocialPlatform.TWITTER)
    assert result is None


@pytest.mark.asyncio
async def test_generate_variant_for_platform_success(llm_service, mock_agent_twitter):
    result = await llm_service.generate_variant_for_platform("AI text", SocialPlatform.TWITTER, "")
    assert result is not None
    assert result.platform == SocialPlatform.TWITTER
    mock_agent_twitter.generate_variant.assert_called_once_with("AI text", "")


@pytest.mark.asyncio
async def test_generate_variant_for_platform_unsupported(llm_service):
    with pytest.raises(ValueError, match="Unsupported platform agent"):
        await llm_service.generate_variant_for_platform("Text", SocialPlatform.FACEBOOK)


@pytest.mark.asyncio
async def test_generate_variant_for_platform_failing_agent(llm_service, mock_agent_twitter):
    mock_agent_twitter.generate_variant.side_effect = RuntimeError("API down")
    with pytest.raises(RuntimeError, match="API down"):
        await llm_service.generate_variant_for_platform("Text", SocialPlatform.TWITTER, "")

