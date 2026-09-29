from typing import Type, List
from services.publishers.social_publisher import SocialPublisher


_PUBLISHER_REGISTRY: List[Type[SocialPublisher]] = []


def register_publisher(cls: Type[SocialPublisher]) -> Type[SocialPublisher]:
    """
    Decorator used to explicitly register a social publisher in the pipeline.
    """
    if cls not in _PUBLISHER_REGISTRY:
        _PUBLISHER_REGISTRY.append(cls)
    return cls


def get_registered_publishers() -> List[Type[SocialPublisher]]:
    """
    Returns the complete list of publisher classes registered with @register_publisher.
    """
    return _PUBLISHER_REGISTRY