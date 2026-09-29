from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from schemas.publisher_schemas import PublisherResponse


class SocialPublisher(ABC):
    def __init__(self, platform: str):
        self.platform = platform

    @abstractmethod
    async def publish(
        self, content: str, metadata: Optional[Dict[str, Any]] = None
    ) -> PublisherResponse:
        pass