import re
from typing import Optional
from services.agents.base_agent import BaseAgent
from services.agents.registry import register_agent


@register_agent
class FacebookAgent(BaseAgent):
    """
    Facebook-specific AI agent responsible for generating warm, engaging,
    community-focused, and conversational posts.
    """

    MIN_LENGTH = 30
    MAX_LENGTH = 2000
    MIN_HASHTAGS = 0
    MAX_HASHTAGS = 5
    FORBIDDEN_PLACEHOLDERS = [
        "[insert",
        "[votre nom]",
        "[lien]",
        "[link]",
        "here is your post",
        "as an ai",
    ]

    def __init__(self):
        super().__init__(platform_name="facebook")

    def build_prompt(self, source_text: str) -> str:
        return f"""
Adapt the following content into an engaging Facebook post.

Guidelines:
- Warm, friendly, and conversational tone that encourages community discussion.
- Use natural storytelling or relatable context where appropriate.
- Use emojis moderately to add expression and visual hierarchy.
- Include a clear call-to-action or open-ended question to drive comments.
- Include 1 to 3 relevant hashtags (avoid overusing hashtags on Facebook).
- Break long text into readable paragraphs with clean line breaks.

Source Text:
{source_text}
"""

    def validate(self, content: str) -> tuple[bool, Optional[str]]:
        """
        Strict deterministic validation for a Facebook post.
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

        
        text_lower = text.lower()
        found_placeholders = [
            ph for ph in self.FORBIDDEN_PLACEHOLDERS if ph in text_lower
        ]
        if found_placeholders:
            errors.append(
                f"Forbidden placeholder(s) detected: {', '.join(repr(ph) for ph in found_placeholders)}."
            )

        
        hashtags = re.findall(r"#\w+", text)
        if not (self.MIN_HASHTAGS <= len(hashtags) <= self.MAX_HASHTAGS):
            errors.append(
                f"Hashtag count ({len(hashtags)}) outside range [{self.MIN_HASHTAGS}-{self.MAX_HASHTAGS}]."
            )

        
        lines = [line for line in text.split("\n") if line.strip()]
        if length > 300 and len(lines) < 2:
            errors.append(
                "Text is too long (>300 chars) to consist of a single paragraph."
            )

        # Final verdict
        if errors:
            return False, " | ".join(errors)

        return True, None