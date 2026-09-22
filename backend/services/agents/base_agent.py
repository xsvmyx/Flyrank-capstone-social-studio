from abc import ABC, abstractmethod
from typing import Optional
from groq import AsyncGroq
from config.connections import get_groq_client
from config.settings import logger
from schemas.variant_schemas import GeneratedVariant,SocialPlatform
from config.settings import GROQ_MODEL

class BaseAgent(ABC):
    """
    Abstract Base Class for all platform-specific LLM agents.
    Encapsulates the Groq client execution and variant generation workflow.
    """

    def __init__(
        self,
        platform_name: str,
        model_name: str = GROQ_MODEL,
        groq_client: Optional[AsyncGroq] = None,
    ):
        self.platform_name = platform_name
        self.model_name = model_name
        
        self.client = groq_client or get_groq_client()

    @abstractmethod
    def build_prompt(self, source_text: str) -> str:
        """
        Abstract method to be overridden by concrete agent subclasses.
        Defines platform-specific formatting rules, tone, and prompt constraints.
        """
        pass


    @abstractmethod
    def validate(self, content: str) -> tuple[bool, Optional[str]]:
        """
        Retourns (True, None) if valid,
        or (False, "reason of failure") if invalid.
        """
        pass




    MAX_RETRIES = 2  

    async def generate_variant(self, source_text: str) -> GeneratedVariant:
        """
        Executes LLM completion request with an automatic retry loop if validation fails.
        """
        logger.info(f"🤖 Generating variant for [{self.platform_name.upper()}] using Groq ({self.model_name})...")

        prompt = self.build_prompt(source_text)
        
        
        messages = [
            {
                "role": "system",
                "content": f"You are an expert social media manager specialized in {self.platform_name} content creation.",
            },
            {
                "role": "user",
                "content": prompt,
            },
        ]

        attempt = 0
        raw_response = ""
        is_valid = False
        validation_error = None

        while attempt <= self.MAX_RETRIES:
            attempt += 1
            if attempt > 1:
                logger.warning(f"🔄 [RETRY {attempt-1}/{self.MAX_RETRIES}] Re-generating for [{self.platform_name.upper()}] due to validation failure...")

            
            chat_completion = await self.client.chat.completions.create(
                messages=messages,
                model=self.model_name,
                temperature=0.7,
            )

            raw_response = chat_completion.choices[0].message.content.strip()

            
            is_valid, validation_error = self.validate(raw_response)

            if is_valid:
                logger.info(f"✅ Validation passed for [{self.platform_name.upper()}] on attempt {attempt}.")
                break

            
            logger.warning(
                f"⚠️ Validation failed on attempt {attempt} for [{self.platform_name.upper()}]: {validation_error}"
            )

            if attempt <= self.MAX_RETRIES:
                messages.append({"role": "assistant", "content": raw_response})
                messages.append({
                    "role": "user",
                    "content": (
                        f"Your output failed validation for the following reason(s):\n"
                        f"{validation_error}\n\n"
                        f"Please regenerate the content fixing ONLY these issues while keeping the core message."
                    ),
                })

        
        return GeneratedVariant(
            platform=SocialPlatform(self.platform_name.lower()),
            content=raw_response,
            hashtags=[],
            is_valid=is_valid,
            error_msg="",
            validation_error=validation_error if not is_valid else None,
        )




    async def regenerate_variant(
        self, 
        source_text: str, 
        error_message: Optional[str] = None
    ) -> GeneratedVariant:
        """
        Executes LLM completion request incorporating previous user feedback / error message,
        with an automatic retry loop if local validation fails.
        """
        logger.info(f"🔄 Regenerating variant for [{self.platform_name.upper()}] with feedback...")

        base_prompt = self.build_prompt(source_text)

        
        user_prompt = base_prompt
        if error_message and error_message.strip():
            user_prompt += (
                f"\n\n--- CRITICAL CORRECTION REQUIRED ---\n"
                f"The previous attempt for this post was rejected or failed with the following feedback/error:\n"
                f"\"{error_message}\"\n\n"
                f"Please regenerate the post taking into full account this feedback while maintaining "
                f"the required formatting for {self.platform_name}."
            )

        messages = [
            {
                "role": "system",
                "content": f"You are an expert social media manager specialized in {self.platform_name} content creation.",
            },
            {
                "role": "user",
                "content": user_prompt,
            },
        ]

        attempt = 0
        raw_response = ""
        is_valid = False
        validation_error = None

        while attempt <= self.MAX_RETRIES:
            attempt += 1
            if attempt > 1:
                logger.warning(f"🔄 [RETRY {attempt-1}/{self.MAX_RETRIES}] Re-generating for [{self.platform_name.upper()}] due to local validation failure...")

            chat_completion = await self.client.chat.completions.create(
                messages=messages,
                model=self.model_name,
                temperature=0.7,
            )

            raw_response = chat_completion.choices[0].message.content.strip()

            is_valid, validation_error = self.validate(raw_response)

            if is_valid:
                logger.info(f"✅ Validation passed for [{self.platform_name.upper()}] on attempt {attempt}.")
                break

            logger.warning(
                f"⚠️ Local validation failed on attempt {attempt} for [{self.platform_name.upper()}]: {validation_error}"
            )

            if attempt <= self.MAX_RETRIES:
                messages.append({"role": "assistant", "content": raw_response})
                messages.append({
                    "role": "user",
                    "content": (
                        f"Your output failed validation for the following reason(s):\n"
                        f"{validation_error}\n\n"
                        f"Please regenerate the content fixing ONLY these issues while keeping the core message."
                    ),
                })

        return GeneratedVariant(
            platform=SocialPlatform(self.platform_name.lower()),
            content=raw_response,
            hashtags=[],
            is_valid=is_valid,
            validation_error=validation_error if not is_valid else None,
        )