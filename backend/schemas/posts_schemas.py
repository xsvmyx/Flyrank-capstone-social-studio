from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class RawPostCreate(BaseModel):
    title: str
    raw_content: str
    image_url: Optional[str] = None


class RawPostResponse(BaseModel):
    id: str
    title: str
    raw_content: str
    image_url: Optional[str] = None
    user_id: str
    created_at: Optional[datetime] = None



class RegeneratePostResponse(BaseModel):
    message: str
    msg_id: int
    post_id: str
