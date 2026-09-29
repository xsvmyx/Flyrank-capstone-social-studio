import importlib
import pkgutil
from pathlib import Path
from typing import Dict, Optional
from schemas.variant_schemas import VariantResponse
from schemas.publisher_schemas import PublisherResponse 
from fastapi import HTTPException, status

from config.settings import logger
from repositories.publish_history_repository import PublishHistoryRepository
from repositories.variant_repository import VariantRepository
from schemas.publish_history_schemas import PublishHistoryCreate
from schemas.variant_schemas import VariantStatus
from services.publishers.social_publisher import SocialPublisher
from services.publishers.registry import get_registered_publishers


class PublishService:

    def __init__(
        self,
        publish_history_repo: PublishHistoryRepository,
        variant_repo: VariantRepository,
    ):
        self.publish_history_repo = publish_history_repo
        self.variant_repo = variant_repo
        
        self._load_publisher_modules()
        self._publishers: Dict[str, SocialPublisher] = self._instantiate_publishers()

    def _load_publisher_modules(self) -> None:
        """
        Dynamically scans and imports modules inside the publishers directory.
        Importing these files triggers the execution of the @register_publisher decorators.
        """
        publishers_dir = Path(__file__).resolve().parent / "publishers"

        for _, module_name, is_pkg in pkgutil.iter_modules([str(publishers_dir)]):
            if not is_pkg and module_name not in ("social_publisher", "registry", "schemas"):
                importlib.import_module(f"services.publishers.{module_name}")

    def _instantiate_publishers(self) -> Dict[str, SocialPublisher]:
        """
        Retrieves all publisher classes registered via the decorator and instantiates them,
        mapping them by their platform identifier.
        """
        publisher_classes = get_registered_publishers()
        instances: Dict[str, SocialPublisher] = {}

        for pub_cls in publisher_classes:
            instance = pub_cls()
            platform_key = instance.platform.lower().strip()
            instances[platform_key] = instance

        logger.info(
            f"🧩 PublishService initialized with {len(instances)} registered publisher(s): "
            f"{list(instances.keys())}"
        )
        return instances

    def get_publisher(self, platform: str) -> SocialPublisher:
        normalized_platform = platform.lower().strip()
        publisher = self._publishers.get(normalized_platform)
        
        if not publisher:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported platform '{platform}'. Available platforms: {list(self._publishers.keys())}"
            )
        return publisher

    async def trigger_publication(self, variant_id: str):

        existing_history_list = await self.publish_history_repo.get_by_variant_id(variant_id)

        if existing_history_list:
            existing_history = existing_history_list[0]
            if existing_history.status == "success":
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Variant {variant_id} has already been successfully published.",
                )
            elif existing_history.status == "pending":
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Publication request for variant {variant_id} is already pending.",
                )
            elif existing_history.status == "failed":
                logger.info(f"🔄 Retrying failed publication for Variant: {variant_id}. Deleting old history...")
                await self.publish_history_repo.delete_by_variant_id(variant_id)

        variant = await self.variant_repo.get_by_id(variant_id)
        if not variant:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Variant with ID {variant_id} not found.",
            )

        if variant.status != VariantStatus.APPROVED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Variant cannot be published because its status is '{variant.status}'. It must be 'approved'."
            )

        publish_data = PublishHistoryCreate(
            variant_id=variant_id,
            idempotency_key=f"publish:{variant_id}",
            status="pending",
        )

        new_publish_record = await self.publish_history_repo.create(history_data=publish_data)

        logger.info(
            f"🚀 Publication job queued for Variant: {variant_id} | History ID: {new_publish_record.id}"
        )

        return new_publish_record



    async def publish_variant(self, variant: VariantResponse,image_url: Optional[str] = None) -> PublisherResponse:
        """
        Prend un variant en paramètre, détermine la plateforme cible, 
        récupère le publisher adéquat via le registre et exécute la publication.
        """
        
        platform_name = (
            variant.platform.value
            if hasattr(variant.platform, "value")
            else str(variant.platform)
        )

        logger.info(f"🚀 Récupération du publisher pour la plateforme : {platform_name}")

        
        publisher = self.get_publisher(platform_name)

        
        logger.info(f"📤 Envoi du contenu pour le variant ID: {variant.id}...")
        
        publish_response = await publisher.publish(
            content=variant.content,
            metadata=variant.metadata,
            image_url=image_url
        )

        logger.info(f"✅ Publication réussie pour le variant ID: {variant.id} sur {platform_name}")
        
        return publish_response