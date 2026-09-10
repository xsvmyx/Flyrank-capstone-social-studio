from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional, List
from pydantic import BaseModel, ConfigDict, Field


class SocialPlatform(str, Enum):
    LINKEDIN = "linkedin"
    TWITTER = "twitter"
    INSTAGRAM = "instagram"
    FACEBOOK = "facebook"


class VariantStatus(str, Enum):
    DRAFT = "draft"         
    APPROVED = "approved"   
    REJECTED = "rejected"   
    PUBLISHED = "published"


class GeneratedVariant(BaseModel):
    """
    Schema for variants produced in-memory by LLMService agents.
    Carries the generated content along with its deterministic validation status.
    """
    platform: SocialPlatform = Field(
        description="Target social media platform"
    )
    content: str = Field(
        description="Generated post content tailored for the platform"
    )
    hashtags: List[str] = Field(
        default_factory=list, 
        description="List of extracted or generated hashtags"
    )
    is_valid: bool = Field(
        default=True, 
        description="Indicates if the generated content passed agent validation rules"
    )
    validation_error: Optional[str] = Field(
        default=None, 
        description="Detailed reason(s) if validation failed"
    )


class VariantResponse(BaseModel):
    """
    Schema representing a record retrieved from or stored into the public.variants Supabase table.
    """
    id: str
    post_id: str
    platform: SocialPlatform
    content: str = ""
    status: VariantStatus = VariantStatus.DRAFT
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)




class UpdateStatusRequest(BaseModel):
    status: VariantStatus
    error_message: Optional[str] = None