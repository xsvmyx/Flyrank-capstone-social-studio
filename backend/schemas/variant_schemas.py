from pydantic import BaseModel, Field
from typing import List
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional
from pydantic import BaseModel, ConfigDict, Field


class SocialPlatform(str, Enum):
    LINKEDIN = "linkedin"
    TWITTER = "twitter"
    INSTAGRAM = "instagram"
    FACEBOOK = "facebook"

class GeneratedVariant(BaseModel):
    platform: str = Field(description="Target social media platform (e.g., linkedin, twitter, instagram)")
    content: str = Field(description="Generated post content tailored for the platform")
    hashtags: List[str] = Field(default_factory=list, description="List of extracted or generated hashtags")


class VariantStatus(str, Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    PUBLISHED = "published"


class GeneratedVariant(BaseModel):
    """
    Schema for variants produced in-memory by LLMService agents.
    """
    platform: SocialPlatform
    content: str


class VariantResponse(BaseModel):
    """
    Schema representing a record retrieved from the public.variants Supabase table.
    """
    id: str
    post_id: str
    platform: SocialPlatform
    content: str = ""
    status: VariantStatus = VariantStatus.PENDING
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)