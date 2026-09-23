from pydantic import BaseModel, HttpUrl
from typing import Optional
from datetime import datetime
from enum import Enum


class ScrapingStatus(str, Enum):
    PENDING = "PENDING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class ScrapingRequestCreate(BaseModel):
    url: HttpUrl


class ScrapingRequestResponse(BaseModel):
    id: str
    user_id: str
    url: str
    status: ScrapingStatus
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime