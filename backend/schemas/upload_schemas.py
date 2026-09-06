from pydantic import BaseModel
from typing import List


class UploadResponse(BaseModel):
    image_url: str


class FileListResponse(BaseModel):
    total: int
    files: List[str]
