import httpx
from typing import Dict, Any, Optional
from config.settings import DISCORD_WEBHOOK, logger
from services.publishers.social_publisher import SocialPublisher
from services.publishers.registry import register_publisher  
from schemas.publisher_schemas import PublisherResponse  

@register_publisher
class DiscordPublisher(SocialPublisher):
    """
    Publisher adapter for Discord using Webhooks.
    """
    def __init__(self):
        super().__init__(platform="discord")

    async def publish(
        self, 
        content: str, 
        metadata: Optional[Dict[str, Any]] = None, 
        image_url: Optional[str] = None
    ) -> PublisherResponse:
        webhook_url = DISCORD_WEBHOOK
        
        if not webhook_url:
            logger.error("❌ DISCORD_WEBHOOK is not configured in settings.")
            raise ValueError("Discord webhook URL is missing in application settings.")

        payload = {
            "content": content
        }

        
        embeds = []
        if metadata and "embeds" in metadata:
            embeds = metadata["embeds"]

        # 2. Si une image_url est transmise, on l'ajoute dans un embed Discord
        if image_url:
            logger.info(f"🖼️ Including image in Discord embed: {image_url}")
            embeds.append({
                "image": {
                    "url": image_url
                }
            })

        
        if embeds:
            payload["embeds"] = embeds

        logger.info(f"📤 Sending publication request to Discord Webhook...")

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(webhook_url, json=payload, timeout=10.0)
                
                if response.status_code not in (200, 204):
                    error_detail = response.text
                    logger.error(f"❌ Discord API error [{response.status_code}]: {error_detail}")
                    raise RuntimeError(f"Failed to publish to Discord: {error_detail}")

                logger.info("✅ Successfully published content to Discord.")
                
                response_json = response.json() if response.content else {"success": True}

                return PublisherResponse(
                    success=True,
                    platform=self.platform,
                    status_code=response.status_code,
                    external_post_id=response_json.get("id"), 
                    response_data=response_json
                )

            except httpx.HTTPError as exc:
                logger.error(f"❌ Network error while calling Discord webhook: {str(exc)}")
                raise RuntimeError(f"Network error during Discord publication: {str(exc)}")