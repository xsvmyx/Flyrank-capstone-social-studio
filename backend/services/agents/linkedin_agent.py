from services.agents.base_agent import BaseAgent
from services.agents.registry import register_agent

@register_agent
class LinkedInAgent(BaseAgent):
    """
    LinkedIn-specific AI agent responsible for generating professional,
    structured, and highly engaging long-form posts.
    """

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