from pydantic import BaseModel


class NewRawPost(BaseModel):
    title: str
    raw_content: str 
    image_url: str | None = None