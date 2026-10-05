from typing import Dict, Any, Optional, Tuple
from config.settings import logger
from schemas.posts_schemas import RawPostResponse
from schemas.variant_schemas import GeneratedVariant , VariantResponse , VariantStatus

class VariantGenerationOrchestrator:
    """
    Central orchestrator for the post processing pipeline.
    Connects the PGMQ queue, data access (Repositories),
    and business services (LLM Agents, Validation).
    """

    def __init__(
        self,
        raw_post_repo,
        llm_service,
        variant_repo,
    ):
        self.raw_post_repo = raw_post_repo
        self.llm_service = llm_service
        self.variant_repo = variant_repo

    async def get_platform_statuses_by_post_id(
        self, post_id: str
    ) -> Dict[str, Dict[str, str | None]]:
        """
        Retrieves the statuses of variants for each platform for a given post.
        Delegates to the variant repository.
        """
        logger.info(f"🔍 Fetching variant statuses for post ID: {post_id}")
        return await self.variant_repo.get_platform_statuses_by_post_id(post_id=post_id)



    async def _check_generation_needed(
            self, platform: str, statuses: Dict[str, Dict[str, str | None]]
        ) -> Tuple[bool, Optional[str]]:
            """
            Checks if generation should proceed for a specific platform based on its current status.
            Returns: (should_generate: bool, error_message: Optional[str])
            """
            platform_lower = platform.lower()
            variant_info = statuses.get(platform_lower)

            if not variant_info:
                logger.info(f"✨ No variant found for platform '{platform}'. Proceeding with generation.")
                return True, None

            status = variant_info.get("status")
            error_message = variant_info.get("error_message")

    
            if status == VariantStatus.DRAFT:
                logger.info(f"⏩ Variant for '{platform}' is already in 'draft' state. Skipping generation.")
                return False, None
            elif status == VariantStatus.APPROVED:
                logger.info(f"⏩ Variant for '{platform}' is already 'approved'. Skipping generation.")
                return False, None
            elif status == VariantStatus.PUBLISHED:
                logger.info(f"⏩ Variant for '{platform}' is already 'published'. Skipping generation.")
                return False, None

            elif status == VariantStatus.REJECTED:
                logger.info(f"🔄 Previous variant for '{platform}' failed. Retrying with last error: {error_message}")
                return True, error_message

            logger.info(f"⚠️ Unknown status '{status}' for platform '{platform}'. Proceeding with generation.")
            return True, None




    async def _fetch_and_prepare_source(self, post_id: str) -> Dict[str, Any]:
        """
        Fetches the source post from the database using RawPostRepository.
        """
        logger.info(f"📥 Fetching raw post source for ID: {post_id}")
        
        post: Optional[RawPostResponse] = await self.raw_post_repo.get_by_id(post_id)
        
        if not post:
            logger.error(f"❌ Raw post not found for ID: {post_id}")
            raise ValueError(f"Raw post with ID {post_id} does not exist.")

        return {
            "post_id": post.id,
            "title": post.title,
            "raw_content": post.raw_content,
            "image_url": post.image_url,
            "user_id": post.user_id,
            "created_at": post.created_at.isoformat() if post.created_at else None,
        }



    async def _persist_one_result(
        self,
        post_id: str,
        variant: GeneratedVariant
    ) -> VariantResponse:
        """
        Persists a validated variant into public.variants using VariantRepository.
        """
        try:
            logger.info(
                f"💾 Persisting variant for Post ID: {post_id}..."
            )

            persisted = await self.variant_repo.create_one(
                post_id=post_id,
                variant=variant
            )

            logger.info(
                f"✅ Successfully persisted variant for Post ID: {post_id}"
            )

            return persisted

        except Exception as e:
            logger.error(
                f"❌ Database error persisting variant for Post ID {post_id}: {e}",
                exc_info=True
            )
            raise




    async def execute_job(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Executes the job workflow:
        1. Retrieves variant statuses for the post.
        2. Checks if generation is required for the target platform.
        3. Fetches the source post data if generation is needed.
        4. Triggers the LLM generation.
        5. Persists the generated variant.
        """
        post_id = payload.get("post_id")
        platform = payload.get("platform")

        if not post_id or not platform:
            raise ValueError("Job payload must contain 'post_id' and 'platform'.")

        logger.info(
            f"⚙️ Executing job for Post ID: {post_id} | Platform: {platform}"
        )

        statuses = await self.get_platform_statuses_by_post_id(post_id)

        should_generate, error_message = await self._check_generation_needed(
            platform,
            statuses
        )

        if not should_generate:
            return {
                "status": "skipped",
                "reason": f"Variant for {platform} is already processed/blocked."
            }

        source_data = await self._fetch_and_prepare_source(post_id)
        source_text = source_data.get("raw_content")

        generated_variant = await self.llm_service.generate_variant_for_platform(
            source_text=source_text,
            platform=platform,
            error_message=error_message
        )

        persisted_variant = await self._persist_one_result(
            post_id=post_id,
            variant=generated_variant
        )

        return {
            "status": "success",
            "platform": platform,
            "generated_variant": persisted_variant
        }

