from pydantic import BaseModel, Field
from typing import List


class GeneratedVariant(BaseModel):
    platform: str = Field(description="Target social media platform (e.g., linkedin, twitter, instagram)")
    content: str = Field(description="Generated post content tailored for the platform")
    hashtags: List[str] = Field(default_factory=list, description="List of extracted or generated hashtags")