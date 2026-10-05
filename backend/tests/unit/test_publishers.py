from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from services.publishers.discord_publisher import DiscordPublisher
from services.publishers.facebook_publisher import FacebookPublisher
from services.publishers.linkedin_publisher import LinkedInPublisher


# ==========================================
# Tests for DiscordPublisher
# ==========================================

@pytest.fixture
def discord_publisher():
    return DiscordPublisher()


@pytest.mark.asyncio
async def test_discord_publisher_success(discord_publisher):
    with patch("services.publishers.discord_publisher.DISCORD_WEBHOOK", "https://discord.local/webhook"):
        with patch("httpx.AsyncClient.post") as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.content = b'{"id": "discord_msg_123"}'
            mock_response.json = lambda: {"id": "discord_msg_123"}
            mock_post.return_value = mock_response

            response = await discord_publisher.publish(content="Hello Discord!")

            assert response.success is True
            assert response.platform == "discord"
            assert response.external_post_id == "discord_msg_123"
            assert response.status_code == 200

            mock_post.assert_called_once_with(
                "https://discord.local/webhook",
                json={"content": "Hello Discord!"},
                timeout=10.0
            )


@pytest.mark.asyncio
async def test_discord_publisher_with_image_and_embeds(discord_publisher):
    with patch("services.publishers.discord_publisher.DISCORD_WEBHOOK", "https://discord.local/webhook"):
        with patch("httpx.AsyncClient.post") as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 204
            mock_response.content = b""
            mock_response.json.side_effect = ValueError("No JSON object could be decoded")
            mock_post.return_value = mock_response

            response = await discord_publisher.publish(
                content="Check out this image!",
                metadata={"embeds": [{"title": "Super Cool"}]},
                image_url="https://example.com/image.png"
            )

            assert response.success is True
            assert response.status_code == 204

            # Ensure image was appended to embeds
            call_kwargs = mock_post.call_args[1]
            payload = call_kwargs["json"]
            assert len(payload["embeds"]) == 2
            assert payload["embeds"][0]["title"] == "Super Cool"
            assert payload["embeds"][1]["image"]["url"] == "https://example.com/image.png"


@pytest.mark.asyncio
async def test_discord_publisher_missing_webhookURL(discord_publisher):
    # Patch DISCORD_WEBHOOK to be empty/None
    with patch("services.publishers.discord_publisher.DISCORD_WEBHOOK", None):
        with pytest.raises(ValueError, match="Discord webhook URL is missing"):
            await discord_publisher.publish(content="Hello")


@pytest.mark.asyncio
async def test_discord_publisher_http_error(discord_publisher):
    with patch("services.publishers.discord_publisher.DISCORD_WEBHOOK", "https://discord.local/webhook"):
        with patch("httpx.AsyncClient.post") as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 403
            mock_response.text = "Forbidden"
            mock_post.return_value = mock_response

            with pytest.raises(RuntimeError, match="Failed to publish to Discord: Forbidden"):
                await discord_publisher.publish(content="Bad request")


@pytest.mark.asyncio
async def test_discord_publisher_network_error(discord_publisher):
    with patch("services.publishers.discord_publisher.DISCORD_WEBHOOK", "https://discord.local/webhook"):
        with patch("httpx.AsyncClient.post") as mock_post:
            mock_post.side_effect = httpx.ConnectError("Connection refused")

            with pytest.raises(RuntimeError, match="Network error during Discord publication: Connection refused"):
                await discord_publisher.publish(content="Network down")


# ==========================================
# Tests for Mock Publishers
# ==========================================

@pytest.mark.asyncio
async def test_facebook_publisher_mock():
    publisher = FacebookPublisher()
    assert publisher.platform == "facebook"

    response = await publisher.publish(content="Mock post")

    assert response.success is True
    assert response.platform == "facebook"
    assert response.status_code == 200
    assert response.external_post_id == "mock_fb_post_123456789"


@pytest.mark.asyncio
async def test_linkedin_publisher_mock():
    publisher = LinkedInPublisher()
    assert publisher.platform == "linkedin"

    response = await publisher.publish(content="Mock post")

    assert response.success is True
    assert response.platform == "linkedin"
    assert response.status_code == 200
    assert response.external_post_id == "mock_li_post_123456789"
