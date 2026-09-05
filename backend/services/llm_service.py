from config.settings import logger
from config.config import groq_client, GROQ_MODEL


class GroqService:
    def __init__(self):
        self.client = groq_client
        self.system_prompt = (
            "You are an expert social media copywriter. "
            "Repurpose raw post content into high-converting posts for LinkedIn and Twitter."
        )

    async def call_llm(self, payload: dict) -> str:
        """
        Handles prompt construction, API execution, and response parsing.
        """
        
        post_id = payload.get("post_id") or payload.get("id")

        
        raw_content = (
            payload.get("raw_content")
            or payload.get("content")
            or payload.get("text")
            or payload.get("raw_text")
            or ""
        )

        if not raw_content:
            logger.error(f"❌ Empty payload payload structure: {payload}")
            raise ValueError(f"Payload for post #{post_id} contains no text content.")

        user_prompt = f"Repurpose the following content for LinkedIn:\n\n{raw_content}"

        logger.info(f"⏳ Sending request to Groq API for post ID: {post_id}...")

        try:
            response = await self.client.chat.completions.create(
                model=GROQ_MODEL,
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.7,
                max_tokens=1024
            )
            generated_text = response.choices[0].message.content
            return generated_text

        except Exception as e:
            logger.error(f"❌ Groq API call failed for post ID {post_id}: {e}")
            raise