from uuid import UUID
from typing import Any, Dict, Optional
from config.settings import logger
from repositories.variant_repository import VariantRepository
from repositories.publish_history_repository import PublishHistoryRepository
from services.publish_service import PublishService
from schemas.variant_schemas import VariantStatus, VariantResponse 
from schemas.publish_history_schemas import PublishHistoryUpdate
from repositories.raw_post_repository import RawPostRepository

class VariantPublishingOrchestrator:
    def __init__(
        self,
        variant_repository: VariantRepository,
        publish_history_repository: PublishHistoryRepository,
        raw_post_repositroy: RawPostRepository,
        publish_service: PublishService,
    ):
        self.variant_repository = variant_repository
        self.publish_history_repository = publish_history_repository
        self.raw_post_repository = raw_post_repositroy
        self.publish_service = publish_service

    async def fetch_variant(self, variant_id: UUID | str) -> VariantResponse:
        str_variant_id = str(variant_id)

        variant = await self.variant_repository.get_by_id(str_variant_id)

        if not variant:
            logger.error(
                f"❌ Variant with ID {str_variant_id} not found in database."
            )
            raise ValueError(
                f"Variant with ID {str_variant_id} not found."
            )

        if variant.status != VariantStatus.APPROVED:
            logger.warning(
                f"⚠️ Attempt to publish variant {str_variant_id} with invalid status: "
                f"'{variant.status}'. Required status: 'approved'."
            )
            raise ValueError(
                f"Variant cannot be published because its status is "
                f"'{variant.status}'. It must be 'approved'."
            )

        logger.info(
            f"✅ Variant {str_variant_id} successfully fetched and validated "
            f"for platform '{variant.platform}'."
        )
        return variant



    async def update_variant_state(
        self,
        variant_id: UUID | str,
        status: VariantStatus,
        error_message: Optional[str] = None
    ) -> Optional[Any]:
        """
        Updates the variant status in the variants table (e.g., PUBLISHED).
        """
        str_variant_id = str(variant_id)

        updated_variant = await self.variant_repository.update_status_by_id(
            variant_id=str_variant_id,
            status=status,
            error_message=error_message
        )

        logger.info(
            f"✨ Variant {str_variant_id} state updated to: '{status}'"
        )

        return updated_variant

    async def update_history_state(
        self,
        history_id: UUID | str,
        status: str,
        response_payload: Optional[Dict[str, Any]] = None,
        error_message: Optional[str] = None
    ) -> None:
        update_data = PublishHistoryUpdate(
            status=status,
            response_payload=response_payload or {},
            error_message=error_message
        )

        await self.publish_history_repository.update(
            history_id,
            update_data
        )

        logger.info(
            f"📝 Publish history {history_id} updated to status: '{status}'"
        )





    async def publish(self, variant: VariantResponse, image_url: Optional[str] = None) -> Dict[str, Any]:
            """Execute the publication process for a variant using the dedicated publishing service"""

            result = await self.publish_service.publish_variant(variant=variant, image_url=image_url)

            platform_name = (
                variant.platform.value
                if hasattr(variant.platform, "value")
                else str(variant.platform)
            )


            if result:
                if hasattr(result, "model_dump"):
                    return result.model_dump()
                if isinstance(result, dict):
                    return result

            return {
                "status": "success",
                "platform": platform_name
            }

    async def execute_job(self, payload: Dict[str, Any]) -> None:
        """Orchestrate the async worker job for variant publication.
        
        Args:
            payload: Dictionary containing job arguments (history_id, variant_id, etc.)
        """
        history_id = payload.get("history_id")
        variant_id = payload.get("variant_id")

        try:
            logger.info(
                f"🚀 Starting publishing workflow for Variant: {variant_id} "
                f"(History: {history_id})"
            )

            
            variant = await self.variant_repository.get_by_id(str(variant_id))

            if not variant:
                raise ValueError(f"Variant with ID {variant_id} not found.")

            
            if variant.status != VariantStatus.APPROVED:
                error_msg = (
                    f"Variant cannot be published because its status is "
                    f"'{variant.status}'. It must be 'approved'."
                )
                logger.warning(f"⚠️ {error_msg}")

                if history_id:
                    await self.update_history_state(
                        history_id=history_id,
                        status="failed",
                        error_message=error_msg
                    )
                return

            platform_name = (
                variant.platform.value
                if hasattr(variant.platform, "value")
                else str(variant.platform)
            )
            logger.info(f"PLATFORM: {platform_name}")


            url = await self.raw_post_repository.get_image_url_by_id(variant.post_id)

            logger.info(f"LINK : {url}")
            
            publish_response = await self.publish(variant=variant,image_url = url)

            
            if history_id:
                await self.update_history_state(
                    history_id=history_id,
                    status="success",
                    response_payload=publish_response
                )

            
            await self.update_variant_state(
                variant_id=variant_id,
                status=VariantStatus.PUBLISHED
            )

            logger.info(
                f"🎉 Publishing workflow completed successfully "
                f"for Variant: {variant_id}"
            )

        except Exception as e:
            error_msg = str(e)
            logger.error(
                f"❌ Publishing job failed for Variant {variant_id}: {error_msg}"
            )

        
            if history_id:
                try:
                    await self.update_history_state(
                        history_id=history_id,
                        status="failed",
                        error_message=error_msg
                    )
                except Exception as db_err:
                    logger.error(
                        f"⚠️ Failed to update publish history status to 'failed': {db_err}"
                    )



##### BETTER ORCHESTRATION , NO POST IF FAILING ....
##### SEMAPHORES IN AGENTS
##### 