from services.agents.base_agent import BaseAgent
from services.agents.registry import register_agent
import re
from typing import Optional

@register_agent
class LinkedInAgent(BaseAgent):
    """
    LinkedIn-specific AI agent responsible for generating professional,
    structured, and highly engaging long-form posts.
    """

    MIN_LENGTH = 30
    MAX_LENGTH = 3000
    MIN_HASHTAGS = 1
    MAX_HASHTAGS = 10
    FORBIDDEN_PLACEHOLDERS = [
        "[insert",
        "[votre nom]",
        "[lien]",
        "[link]",
        "here is your post",
        "as an ai",
    ]


    def __init__(self):
        super().__init__(platform_name="linkedin")

    def build_prompt(self, source_text: str) -> str:
        return f"""
Adapt the following content into an engaging LinkedIn post.

Guidelines:
- Professional yet conversational tone.
- Use line breaks between short sentences for better readability.
- Include a call-to-action or thought-provoking question at the end.
- Include 3 to 5 relevant industry hashtags.

Source Text:
{source_text}
"""


    def validate(self, content: str) -> tuple[bool, Optional[str]]:
            """
            Strict deterministic validation for a LinkedIn post.
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

            
            if errors:
                return False, " | ".join(errors)

            return True, None