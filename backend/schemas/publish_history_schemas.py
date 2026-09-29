from datetime import datetime
from typing import Any, Dict, Optional
from uuid import UUID
from pydantic import BaseModel, Field
from enum import Enum

class VariantPublishStatus(str, Enum):
    SUCCESS = "success"            
    FAILED = "failed"   
    PENDING = "pending"


class VariantPublishTriggerRequest(BaseModel):
    variant_id: UUID


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

    class Config:
        from_attributes = True



