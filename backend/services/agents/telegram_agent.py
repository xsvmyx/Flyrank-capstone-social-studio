import re
from typing import Optional
from services.agents.base_agent import BaseAgent
from services.agents.registry import register_agent


@register_agent
class TelegramAgent(BaseAgent):
    """
    Telegram-specific AI agent responsible for generating clear, 
    engaging broadcast and group chat messages for Telegram channels/groups.
    """

    MIN_LENGTH = 10
    MAX_LENGTH = 4096 

    FORBIDDEN_PATTERNS = [
        r"\[\s*(insert\vert{}votre nom\vert{}lien\vert{}link)[^\]]*\]",
        r"\bhere\s+is\s+your\s+(post|message)\b",
        r"\bas\s+an\s+ai\b",
    ]

    def __init__(self):
        super().__init__(platform_name="telegram")

    def build_prompt(self, source_text: str) -> str:
        safe_source = source_text[:3000] if len(source_text) > 3000 else source_text

        return f"""
Adapt the following content into an engaging Telegram channel post or group message.

Guidelines:
- Direct, informative, and visual tone tailored for mobile reading in Telegram channels.
- Use simple Markdown formatting: **bold** for key concepts and headlines, *italic* for secondary notes, `code` for technical terms/links.
- Structure key takeaways with clear emoji bullet points (e.g. 🔹, 🚀, 💡).
- Keep social media hashtags to a minimum (max 2-3 at the very bottom for search/indexing).
- End with a compelling call-to-action (e.g., asking for feedback, linking to external content, or inviting users to comment).
- HARD LIMIT: Your entire response must be strictly between 100 and 1500 characters.

Source Text:
{safe_source}
"""

    def validate(self, content: str) -> tuple[bool, Optional[str]]:
        """
        Deterministic validation for a Telegram message.
        Collects all violations before returning.
        """
        if not content or not content.strip():
            return False, "Content is empty."

        text = content.strip()
        length = len(text)
        errors: list[str] = []

        if not (self.MIN_LENGTH <= length <= self.MAX_LENGTH):
            errors.append(
                f"Length ({length} chars) outside range [{self.MIN_LENGTH}-{self.MAX_LENGTH}]."
            )

        found_patterns = [
            pattern for pattern in self.FORBIDDEN_PATTERNS
            if re.search(pattern, text, re.IGNORECASE)
        ]
        if found_patterns:
            errors.append(
                f"Forbidden placeholder/AI patterns detected: {', '.join(found_patterns)}."
            )


        hashtags = re.findall(r"(?<!\w)#([a-zA-Z0-9_-]+)", text)
        if len(hashtags) > 3:
            errors.append(
                f"Too many hashtags detected ({len(hashtags)}). Telegram posts should use at most 2-3 indexing hashtags."
            )


        lines = [line for line in text.split("\n") if line.strip()]
        if length > 350 and len(lines) < 2:
            errors.append(
                "Text is too long (>350 chars) without paragraph breaks. Break down into bullet points or distinct paragraphs."
            )

        if errors:
            return False, " | ".join(errors)

        return True, None