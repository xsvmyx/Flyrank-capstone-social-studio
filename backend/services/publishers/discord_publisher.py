# import httpx
# from typing import Dict, Any, Optional
# from config.settings import logger
# from services.publishers.base_publisher import SocialPublisher


# class DiscordPublisher(SocialPublisher):
#     """
#     Adaptateur réel pour publier sur Discord via un Webhook.
#     """

#     def __init__(self, webhook_url: str):
#         if not webhook_url:
#             raise ValueError("DISCORD_WEBHOOK_URL ne doit pas être vide.")
#         self.webhook_url = webhook_url

#     async def publish(
#         self, content: str, metadata: Optional[Dict[str, Any]] = None
#     ) -> Dict[str, Any]:
#         """
#         Publie directement un message sur le canal Discord configuré.
#         """
#         payload = {"content": content}

#         # Possibilité d'enrichir le message Discord si une image est fournie dans metadata
#         if metadata and metadata.get("image_url"):
#             payload["embeds"] = [
#                 {
#                     "title": metadata.get("title", ""),
#                     "image": {"url": metadata["image_url"]},
#                 }
#             ]

#         try:
#             async with httpx.AsyncClient(timeout=10.0) as client:
#                 logger.info("🚀 Publication en cours sur Discord via Webhook...")
#                 response = await client.post(self.webhook_url, json=payload)

#                 # Discord renvoie 204 No Content en cas de succès Webhook standard (ou 200)
#                 if response.status_code in (200, 204):
#                     logger.info("✅ Publication Discord réussie !")
#                     return {
#                         "status": "success",
#                         "platform": "discord",
#                         "response_code": response.status_code,
#                     }

#                 response.raise_for_status()

#         except httpx.HTTPStatusError as e:
#             logger.error(
#                 f"❌ Échec de publication Discord (HTTP {e.response.status_code}): {e.response.text}"
#             )
#             raise e
#         except Exception as e:
#             logger.error(
#                 f"❌ Erreur inattendue lors de la publication Discord: {e}"
#             )
#             raise e
