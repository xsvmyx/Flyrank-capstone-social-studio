import urllib.error
from io import BytesIO
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from repositories.raw_post_repository import RawPostRepository
from repositories.scraping_repository import ScrapingRepository
from schemas.scraping_schemas import ScrapingStatus
from services.scraping_service import ScrapingService


@pytest.fixture
def mock_scraping_repo():
    repo = MagicMock(spec=ScrapingRepository)
    repo.update_status = AsyncMock()
    return repo


@pytest.fixture
def mock_raw_post_repo():
    repo = MagicMock(spec=RawPostRepository)
    repo.create = AsyncMock(return_value=MagicMock(id=101))
    return repo


@pytest.fixture
def scraping_service(mock_scraping_repo, mock_raw_post_repo):
    return ScrapingService(
        scraping_repo=mock_scraping_repo,
        raw_post_repo=mock_raw_post_repo,
    )


# ==========================================
# 1. Tests for URL Validation (_is_valid_url)
# ==========================================

def test_is_valid_url_valid_http(scraping_service):
    assert scraping_service._is_valid_url("http://example.com") is True
    assert scraping_service._is_valid_url("https://sub.domain.com/path?arg=1") is True


def test_is_valid_url_invalid(scraping_service):
    assert scraping_service._is_valid_url("ftp://example.com") is False
    assert scraping_service._is_valid_url("not_a_url") is False
    assert scraping_service._is_valid_url("") is False


# ==========================================
# 2. Tests for Page Scraping (scrape_page)
# ==========================================

@pytest.mark.asyncio
async def test_scrape_page_invalid_url_raises(scraping_service):
    with pytest.raises(ValueError, match="Invalid URL format"):
        await scraping_service.scrape_page("invalid-url")


@pytest.mark.asyncio
async def test_scrape_page_success(scraping_service):
    html_data = (
        "<html>"
        "<head>"
        "<title>Test Article Title</title>"
        '<meta property="og:image" content="https://example.com/image.jpg" />'
        "</head>"
        "<body>"
        "<script>console.log('ignore me');</script>"
        "<style>body { color: red; }</style>"
        "<p>Hello <b>World</b>! This is a test article.</p>"
        "</body>"
        "</html>"
    ).encode("utf-8")

    mock_response = MagicMock()
    mock_response.read.return_value = html_data
    mock_response.__enter__.return_value = mock_response

    with patch("urllib.request.urlopen", return_value=mock_response):
        title, text, image_url = await scraping_service.scrape_page("https://example.com/article")

    assert title == "Test Article Title"
    # Option 1: Match the exact extracted text output
    assert "Hello World ! This is a test article." in text
    assert "script" not in text
    assert image_url == "https://example.com/image.jpg"


@pytest.mark.asyncio
async def test_scrape_page_relative_image_url(scraping_service):
    html_data = (
        "<html>"
        "<head>"
        '<meta property="og:image" content="/assets/cover.png" />'
        "</head>"
        "<body><p>Some content</p></body>"
        "</html>"
    ).encode("utf-8")

    mock_response = MagicMock()
    mock_response.read.return_value = html_data
    mock_response.__enter__.return_value = mock_response

    with patch("urllib.request.urlopen", return_value=mock_response):
        _, _, image_url = await scraping_service.scrape_page("https://example.com/blog/post-1")

    assert image_url == "https://example.com/assets/cover.png"


@pytest.mark.asyncio
async def test_scrape_page_twitter_image_fallback(scraping_service):
    html_data = (
        "<html>"
        "<head>"
        '<meta name="twitter:image" content="https://example.com/twitter-card.jpg" />'
        "</head>"
        "<body><p>Content</p></body>"
        "</html>"
    ).encode("utf-8")

    mock_response = MagicMock()
    mock_response.read.return_value = html_data
    mock_response.__enter__.return_value = mock_response

    with patch("urllib.request.urlopen", return_value=mock_response):
        _, _, image_url = await scraping_service.scrape_page("https://example.com")

    assert image_url == "https://example.com/twitter-card.jpg"


@pytest.mark.asyncio
async def test_scrape_page_no_title_fallback(scraping_service):
    html_data = b"<html><body><p>No title here</p></body></html>"

    mock_response = MagicMock()
    mock_response.read.return_value = html_data
    mock_response.__enter__.return_value = mock_response

    with patch("urllib.request.urlopen", return_value=mock_response):
        title, text, image_url = await scraping_service.scrape_page("https://myblog.org/news")

    assert title == "Article from myblog.org"
    assert text == "No title here"
    assert image_url is None


# ==========================================
# 3. Tests for Orchestration (execute_scraping)
# ==========================================

@pytest.mark.asyncio
async def test_execute_scraping_success(scraping_service, mock_scraping_repo, mock_raw_post_repo):
    payload = {
        "scraping_request_id": 42,
        "url": "https://example.com/article",
        "user_id": "usr_789",
    }

    with patch.object(
        scraping_service,
        "scrape_page",
        AsyncMock(return_value=("My Title", "My Content", "https://example.com/img.jpg")),
    ):
        await scraping_service.execute_scraping(payload)

    # Verify RawPostRepository.create was called
    mock_raw_post_repo.create.assert_called_once()
    create_args = mock_raw_post_repo.create.call_args[1]
    assert create_args["user_id"] == "usr_789"
    assert create_args["post_data"].title == "My Title"
    assert create_args["post_data"].raw_content == "My Content"
    assert create_args["post_data"].image_url == "https://example.com/img.jpg"

    # Verify ScrapingRepository.update_status was called with COMPLETED
    mock_scraping_repo.update_status.assert_called_once_with(
        request_id=42,
        status=ScrapingStatus.COMPLETED,
    )


@pytest.mark.asyncio
async def test_execute_scraping_missing_url(scraping_service, mock_scraping_repo):
    payload = {"scraping_request_id": 10, "user_id": "usr_123"}

    with pytest.raises(ValueError, match="Payload missing valid 'url' key"):
        await scraping_service.execute_scraping(payload)

    mock_scraping_repo.update_status.assert_called_once_with(
        request_id=10,
        status=ScrapingStatus.FAILED,
        error_message="Payload missing valid 'url' key",
    )


@pytest.mark.asyncio
async def test_execute_scraping_missing_user_id(scraping_service, mock_scraping_repo):
    payload = {"scraping_request_id": 11, "url": "https://example.com"}

    with pytest.raises(ValueError, match="Payload missing required 'user_id' key"):
        await scraping_service.execute_scraping(payload)

    mock_scraping_repo.update_status.assert_called_once_with(
        request_id=11,
        status=ScrapingStatus.FAILED,
        error_message="Payload missing required 'user_id' key",
    )


@pytest.mark.asyncio
async def test_execute_scraping_http_error_handled(scraping_service, mock_scraping_repo):
    payload = {
        "scraping_request_id": 99,
        "url": "https://example.com/404",
        "user_id": "usr_123",
    }

    http_error = urllib.error.HTTPError(
        url="https://example.com/404",
        code=404,
        msg="Not Found",
        hdrs={},
        fp=BytesIO(b""),
    )

    with patch.object(scraping_service, "scrape_page", AsyncMock(side_effect=http_error)):
        with pytest.raises(urllib.error.HTTPError):
            await scraping_service.execute_scraping(payload)

    mock_scraping_repo.update_status.assert_called_once_with(
        request_id=99,
        status=ScrapingStatus.FAILED,
        error_message="HTTP Error 404: Not Found",
    )


@pytest.mark.asyncio
async def test_execute_scraping_url_error_handled(scraping_service, mock_scraping_repo):
    payload = {
        "scraping_request_id": 100,
        "url": "https://unreachable-host.com",
        "user_id": "usr_123",
    }

    url_error = urllib.error.URLError(reason="Connection Refused")

    with patch.object(scraping_service, "scrape_page", AsyncMock(side_effect=url_error)):
        with pytest.raises(urllib.error.URLError):
            await scraping_service.execute_scraping(payload)

    mock_scraping_repo.update_status.assert_called_once_with(
        request_id=100,
        status=ScrapingStatus.FAILED,
        error_message="URL/Network Error: Connection Refused",
    )


@pytest.mark.asyncio
async def test_execute_scraping_unexpected_exception_handled(scraping_service, mock_scraping_repo):
    payload = {
        "scraping_request_id": 101,
        "url": "https://example.com",
        "user_id": "usr_123",
    }

    with patch.object(scraping_service, "scrape_page", AsyncMock(side_effect=RuntimeError("Unexpected parsing failure"))):
        with pytest.raises(RuntimeError, match="Unexpected parsing failure"):
            await scraping_service.execute_scraping(payload)

    mock_scraping_repo.update_status.assert_called_once_with(
        request_id=101,
        status=ScrapingStatus.FAILED,
        error_message="Unexpected parsing failure",
    )

