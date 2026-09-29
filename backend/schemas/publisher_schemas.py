from typing import Dict, Any, Optional
from pydantic import BaseModel, Field


class PublisherResponse(BaseModel):
    """
    Standardized response schema returned by all social publishers.
    """
    success: bool
    platform: str
    status_code: int = 200
    external_post_id: Optional[str] = None
    response_data: Dict[str, Any] = Field(default_factory=dict)
    error_message: Optional[str] = None