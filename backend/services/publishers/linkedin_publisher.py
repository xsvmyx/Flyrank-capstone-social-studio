import asyncio
from typing import Dict, Any, Optional
from config.settings import logger
from services.publishers.social_publisher import SocialPublisher
from services.publishers.registry import register_publisher  
from schemas.publisher_schemas import PublisherResponse  

@register_publisher
class LinkedInPublisher(SocialPublisher):
    """
    Mock publisher adapter for LinkedIn.
    """
    def __init__(self):
        super().__init__(platform="linkedin")

    async def publish(
        self, content: str, metadata: Optional[Dict[str, Any]] = None , image_url: Optional[str] = None
    ) -> PublisherResponse:
        
        logger.info(f"📤 [MOCK] Sending publication request to LinkedIn...")
        logger.info(f"📝 [MOCK] Content length: {len(content)} characters")

        await asyncio.sleep(0.5)

        logger.info("✅ [MOCK] Successfully 'published' content to LinkedIn.")

        return PublisherResponse(
            success=True,
            platform=self.platform,
            status_code=200,
            external_post_id="mock_li_post_123456789",
            response_data={
                "message": "Mock publication successful on LinkedIn"
            }
        )