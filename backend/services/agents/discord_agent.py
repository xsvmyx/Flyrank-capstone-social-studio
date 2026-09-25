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
    FORBIDDEN_PLACEHOLDERS = [
        "[insert",
        "[votre nom]",
        "[lien]",
        "[link]",
        "here is your post",
        "as an ai",
    ]

    def __init__(self):
        super().__init__(platform_name="discord")

    def build_prompt(self, source_text: str) -> str:
        return f"""
Adapt the following content into an engaging Discord community message.

Guidelines:
- Direct, casual, and highly conversational tone suited for a chat server.
- Use Discord Markdown formatting: **bold** for emphasis, > for quotes, `#` for headers, `code` for technical terms.
- Use emojis to add visual structure and keep it lively.
- Do NOT use social media hashtags (e.g. #tech, #innovation). You may reference channel names (e.g. #general).
- End with a call-to-action encouraging members to reply or react with emojis.
- Keep line breaks clear for easy reading on mobile and desktop.

Source Text:
{source_text}
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

        text_lower = text.lower()


        found_placeholders = [
            ph for ph in self.FORBIDDEN_PLACEHOLDERS if ph in text_lower
        ]
        if found_placeholders:
            errors.append(
                f"Forbidden placeholder(s) detected: {', '.join(repr(ph) for ph in found_placeholders)}."
            )


        social_hashtags = re.findall(r"(?<!#)(?<!\w)#([a-zA-Z0-9_]+)", text)
        

        common_channels = {"general", "announcements", "help", "welcome", "discussion", "dev", "chat"}
        detected_hashtags = [h for h in social_hashtags if h.lower() not in common_channels]

        if len(detected_hashtags) > 2:
            errors.append(
                f"Social hashtags detected ({', '.join(detected_hashtags)}). Discord content should not rely on social media hashtags."
            )


        lines = [line for line in text.split("\n") if line.strip()]
        if length > 400 and len(lines) < 2:
            errors.append(
                "Text is too long (>400 chars) without line breaks. Format using paragraphs or Discord Markdown lists."
            )

        if errors:
            return False, " | ".join(errors)

        return True, None