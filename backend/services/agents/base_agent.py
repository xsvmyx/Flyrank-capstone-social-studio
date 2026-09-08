from abc import ABC, abstractmethod
from typing import Optional
from groq import Groq
from config.connections import get_groq_client
from config.settings import logger
from schemas.variant_schemas import GeneratedVariant
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
        groq_client: Optional[Groq] = None,
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



    async def generate_variant(self, source_text: str) -> GeneratedVariant:
        """
        Executes the LLM completion request using the Groq API client with
        the platform-specific prompt defined by the child agent.
        """
        logger.info(f"🤖 Generating variant for [{self.platform_name.upper()}] using Groq ({self.model_name})...")
        
        prompt = self.build_prompt(source_text)

        # Synchronous API invocation (can be wrapped with asyncio.to_thread if required)
        chat_completion = self.client.chat.completions.create(
            messages=[
                {
                    "role": "system",
                    "content": f"You are an expert social media manager specialized in {self.platform_name} content creation.",
                },
                {
                    "role": "user",
                    "content": prompt,
                },
            ],
            model=self.model_name,
            temperature=0.7,
        )

        raw_response = chat_completion.choices[0].message.content

        return GeneratedVariant(
            platform=self.platform_name,
            content=raw_response.strip(),
            hashtags=[],  
        )