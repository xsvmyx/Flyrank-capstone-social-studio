import re
import urllib.parse
import urllib.request
from typing import Any, Dict, Optional, Tuple

from repositories.raw_post_repository import RawPostRepository
from repositories.scraping_repository import ScrapingRepository
from schemas.posts_schemas import RawPostCreate
from schemas.scraping_schemas import ScrapingStatus


class ScrapingService:

    def __init__(self, scraping_repo: ScrapingRepository, raw_post_repo: RawPostRepository):
        self.scraping_repo = scraping_repo
        self.raw_post_repo = raw_post_repo

    HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9,fr;q=0.8",
        "Sec-Ch-Ua": '"Chromium";v="128", "Not;A=Brand";v="24"',
        "Sec-Ch-Ua-Mobile": "?0",
        "Sec-Ch-Ua-Platform": '"Linux"',
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
        "Upgrade-Insecure-Requests": "1",
    }

    def _is_valid_url(self, url: str) -> bool:
        """
        Validates the structure and scheme of the given URL string.
        """
        try:
            parsed = urllib.parse.urlparse(url)
            return bool(parsed.scheme in ("http", "https") and parsed.netloc)
        except Exception:
            return False

    async def scrape_page(self, url: str) -> Tuple[str, str, Optional[str]]:
        """
        Fetches HTML in a single request and extracts page title, plain text, and primary cover image URL.
        Returns a tuple of (title, cleaned_text, primary_image_url).
        """
        if not self._is_valid_url(url):
            raise ValueError(f"Invalid URL format or unsupported scheme: '{url}'")

        req = urllib.request.Request(url, headers=self.HEADERS)
        
        with urllib.request.urlopen(req, timeout=10) as response:
            html_content = response.read().decode("utf-8", errors="ignore")

        # 1. Extract HTML title tag
        title_match = re.search(r"<title[^>]*>(.*?)</title>", html_content, re.IGNORECASE | re.DOTALL)
        title = title_match.group(1).strip() if title_match else f"Article from {urllib.parse.urlparse(url).netloc}"
        title = re.sub(r"\s+", " ", title)

        # 2. Extract primary cover image URL (og:image or twitter:image)
        raw_image_url = None
        og_match = re.search(
            r'<meta\s+[^>]*property=["\']og:image["\']\s+[^>]*content=["\']([^"\']+)["\']',
            html_content,
            re.IGNORECASE,
        ) or re.search(
            r'<meta\s+[^>]*content=["\']([^"\']+)["\']\s+[^>]*property=["\']og:image["\']',
            html_content,
            re.IGNORECASE,
        )

        if og_match:
            raw_image_url = og_match.group(1).strip()
        else:
            twitter_match = re.search(
                r'<meta\s+[^>]*name=["\']twitter:image["\']\s+[^>]*content=["\']([^"\']+)["\']',
                html_content,
                re.IGNORECASE,
            ) or re.search(
                r'<meta\s+[^>]*content=["\']([^"\']+)["\']\s+[^>]*name=["\']twitter:image["\']',
                html_content,
                re.IGNORECASE,
            )
            if twitter_match:
                raw_image_url = twitter_match.group(1).strip()

        primary_image_url = None
        if raw_image_url:
            absolute_image_url = urllib.parse.urljoin(url, raw_image_url)
            if absolute_image_url.startswith(("http://", "https://")):
                primary_image_url = absolute_image_url

        # 3. Clean and extract plain text content
        cleaned_html = re.sub(r"<(script|style).*?>.*?</\1>", "", html_content, flags=re.DOTALL | re.IGNORECASE)
        text_content = re.sub(r"<[^>]+>", " ", cleaned_html)
        cleaned_text = re.sub(r"\s+", " ", text_content).strip()

        return title, cleaned_text, primary_image_url

    async def execute_scraping(self, payload: Dict[str, Any]) -> None:
        """
        Main pipeline orchestrating the scraping process.
        Extracts content, persists the RawPost in database, and updates scraping request status.
        """
        scraping_request_id = payload.get("scraping_request_id")
        url = payload.get("url")
        user_id = payload.get("user_id")

        if not url or not isinstance(url, str):
            error_msg = "Payload missing valid 'url' key"
            print(f"❌ {error_msg} for request #{scraping_request_id}")
            if scraping_request_id:
                await self.scraping_repo.update_status(
                    request_id=scraping_request_id,
                    status=ScrapingStatus.FAILED,
                    error_message=error_msg,
                )
            raise ValueError(error_msg)

        if not user_id:
            error_msg = "Payload missing required 'user_id' key"
            print(f"❌ {error_msg} for request #{scraping_request_id}")
            if scraping_request_id:
                await self.scraping_repo.update_status(
                    request_id=scraping_request_id,
                    status=ScrapingStatus.FAILED,
                    error_message=error_msg,
                )
            raise ValueError(error_msg)

        try:
            # 1. Fetch page content and metadata in a single HTTP request
            page_title, scraped_text, primary_image_url = await self.scrape_page(url)

            # 2. Instantiate RawPostCreate schema
            raw_post_data = RawPostCreate(
                title=page_title,
                raw_content=scraped_text,
                image_url=primary_image_url,
            )

            # 3. Persist RawPost in database via repository
            created_post = await self.raw_post_repo.create(
                post_data=raw_post_data,
                user_id=user_id,
            )

            print(f"📄 Scraping Request #{scraping_request_id} processed successfully!")
            print(f"✅ Created RawPost Record ID: {getattr(created_post, 'id', created_post)}")

            # 4. Update status to COMPLETED
            await self.scraping_repo.update_status(
                request_id=scraping_request_id,
                status=ScrapingStatus.COMPLETED,
            )

        except urllib.error.HTTPError as he:
            error_msg = f"HTTP Error {he.code}: {he.reason}"
            print(f"❌ {error_msg} when scraping URL {url} (Request #{scraping_request_id})")
            await self.scraping_repo.update_status(
                request_id=scraping_request_id,
                status=ScrapingStatus.FAILED,
                error_message=error_msg,
            )
            raise he

        except urllib.error.URLError as ue:
            error_msg = f"URL/Network Error: {ue.reason}"
            print(f"❌ {error_msg} when reaching {url} (Request #{scraping_request_id})")
            await self.scraping_repo.update_status(
                request_id=scraping_request_id,
                status=ScrapingStatus.FAILED,
                error_message=error_msg,
            )
            raise ue

        except Exception as e:
            error_msg = str(e)
            print(f"❌ Unexpected failure scraping URL {url} (Request #{scraping_request_id}): {error_msg}")
            await self.scraping_repo.update_status(
                request_id=scraping_request_id,
                status=ScrapingStatus.FAILED,
                error_message=error_msg,
            )
            raise e