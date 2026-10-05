from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID
from pydantic import BaseModel, Field, ConfigDict
from enum import Enum
from schemas.variant_schemas import SocialPlatform


class VariantPublishStatus(str, Enum):
    SUCCESS = "success"            
    FAILED = "failed"   
    PENDING = "pending"


class VariantPublishTriggerRequest(BaseModel):
    variant_id: UUID


class BatchPublishTriggerRequest(BaseModel):
    post_id: str = Field(..., description="Raw post id")
    platforms: Optional[List[SocialPlatform]] = Field(
        default=None,
        description="List of target platforms. If empty or omitted, all platforms will be used."
    )


class BatchPublishJobResult(BaseModel):
    variant_id: str
    platform: SocialPlatform
    status: str
    message: str


class BatchPublishTriggerResponse(BaseModel):
    message: str
    post_id: str
    results: List[BatchPublishJobResult]


class PublishHistoryBase(BaseModel):
    variant_id: UUID
    idempotency_key: str
    status: str = "pending"
    response_payload: Optional[Dict[str, Any]] = Field(default_factory=dict)
    error_message: Optional[str] = None
    attempt_count: int = 1


class PublishHistoryCreate(PublishHistoryBase):
    pass


class PublishHistoryUpdate(BaseModel):
    status: Optional[str] = None
    response_payload: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    attempt_count: Optional[int] = None
    executed_at: Optional[datetime] = None


class PublishHistoryResponse(PublishHistoryBase):
    id: UUID
    executed_at: datetime
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
