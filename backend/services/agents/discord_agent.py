import re
from typing import Optional
from services.agents.base_agent import BaseAgent
from services.agents.registry import register_agent


@register_agent
class DiscordAgent(BaseAgent):
    """
    Discord-specific AI agent responsible for generating engaging, 
    community-focused chat messages leveraging Discord Markdown.
    """

    MIN_LENGTH = 10
    MAX_LENGTH = 2000

    FORBIDDEN_PATTERNS = [
        r"\[\s*(insert\vert{}votre nom\vert{}lien\vert{}link)[^\]]*\]",
        r"\bhere\s+is\s+your\s+(post|message)\b",
        r"\bas\s+an\s+ai\b",
    ]

    def __init__(self):
        super().__init__(platform_name="discord")

    
    def build_prompt(self, source_text: str) -> str:
            # Optionally truncate source text to prevent TPM overflow
            safe_source = source_text[:3000] if len(source_text) > 3000 else source_text

            return f"""
    Adapt the following content into an engaging Discord community message.

    Guidelines:
    - Direct, casual, and highly conversational tone suited for a chat server.
    - Use Discord Markdown formatting: **bold** for emphasis, > for quotes, `#` for headers, `code` for technical terms.
    - Use emojis to add visual structure and keep it lively.
    - Do NOT use social media hashtags (e.g. #tech, #innovation). You may reference channel names (e.g. #general, #announcements).
    - End with a call-to-action encouraging members to reply or react with emojis.
    - Keep line breaks clear for easy reading on mobile and desktop.
    - HARD LIMIT: Your entire response must be strictly between 100 and 1500 characters. Do not write a long essay.

    Source Text:
    {safe_source}
    """


    def validate(self, content: str) -> tuple[bool, Optional[str]]:
        """
        Strict deterministic validation for a Discord message.
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


        social_hashtag_candidates = re.findall(r"(?<!\w)#([a-zA-Z0-9_-]+)", text)
        

        markdown_headers = re.findall(r"^\s*#{1,3}\s+([a-zA-Z0-9_-]+)", text, re.MULTILINE)
        markdown_headers_lower = {h.lower() for h in markdown_headers}

        detected_hashtags = [
            h for h in social_hashtag_candidates 
            if h.lower() not in markdown_headers_lower
        ]

        if len(detected_hashtags) > 4:
            errors.append(
                f"Too many hashtags detected ({', '.join(detected_hashtags)}). Discord content should not rely on social media hashtags."
            )

        lines = [line for line in text.split("\n") if line.strip()]
        if length > 400 and len(lines) < 2:
            errors.append(
                "Text is too long (>400 chars) without line breaks. Format using paragraphs or Discord Markdown lists."
            )

        if errors:
            return False, " | ".join(errors)

        return True, None