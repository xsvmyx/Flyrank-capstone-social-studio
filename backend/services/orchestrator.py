from typing import Dict, Any, Optional, List , Tuple
from config.settings import logger
from services.llm_service import LLMService
from repositories.raw_post_repository import RawPostRepository
from schemas.posts_schemas import RawPostResponse
from schemas.variant_schemas import GeneratedVariant,VariantResponse,VariantStatus
from repositories.variant_repository import VariantRepository


class Orchestrator:
    """
    Central orchestrator for the post processing pipeline.
    Connects the PGMQ queue, data access (Repositories),
    and business services (LLM Agents, Validation).
    """

    def __init__(
        self,
        raw_post_repo: RawPostRepository,
        llm_service: LLMService,
        variant_repo: VariantRepository,
    ):
        self.raw_post_repo = raw_post_repo
        self.llm_service = llm_service
        self.variant_repo = variant_repo


    async def execute_job(self, payload: Dict[str, Any]) -> Dict[str, Any]:
            """
            Main entry point called by the PGMQ Worker.
            Orchestrates the job processing lifecycle using non-approved targets only.
            """
            post_id = payload.get("post_id")

            if not post_id:
                logger.error("❌ Job failed: Payload missing required key 'post_id'")
                raise ValueError("Payload missing required key 'post_id'")

            logger.info(f"⚙️ Executing job for Post ID: {post_id}")

            try:
                # 1. Fetch raw post content
                source_data = await self._fetch_and_prepare_source(post_id)
                content = source_data.get("raw_content")

                if not content or not content.strip():
                    logger.warning(f"⚠️ Post ID {post_id} has empty content. Skipping generation.")
                    return {"status": "skipped", "reason": "empty_content", "post_id": post_id}

                # 2. Fetch targets (DRAFT / REJECTED)
                non_approved_targets = await self._get_non_approved_platforms_with_data(post_id)
                approved_targets = await self._get_approved_platforms_with_data(post_id)

                # 3. Generate / Regenerate
                generated_variants = await self._generate_text_variants(
                    source_text=content,
                    non_approved_targets=non_approved_targets,
                    approved_targets=approved_targets
                )

                if not generated_variants:
                    logger.info(f"⏩ No variants needed or generated for Post ID: {post_id}")
                    return {"status": "skipped", "reason": "nothing_to_generate", "post_id": post_id}

                logger.info(f"✨ Successfully generated/regenerated {len(generated_variants)} variant(s).")

                # 4. Persist
                persisted_results = await self._persist_results(post_id=post_id, variants=generated_variants)

                return {
                    "status": "success", 
                    "post_id": post_id, 
                    "generated_count": len(persisted_results)
                }

            except Exception as e:
                logger.exception(f"❌ Fatal error executing job for Post ID {post_id}: {e}")
                raise e

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



    async def _get_approved_platforms_with_data(self, post_id: str) -> Dict[str, Optional[str]]:
            """
            Fetches existing non-APPROVED variants (DRAFT or REJECTED).
            Returns a mapping of: {platform_name: error_message_or_None}
            """
            existing_variants = await self.variant_repo.get_by_post_id(post_id)
            if not existing_variants:
                return {}

            return {
                (v.platform.value if hasattr(v.platform, "value") else str(v.platform)).lower(): v.error_message
                for v in existing_variants
                if v.status == VariantStatus.APPROVED
            }



    async def _get_non_approved_platforms_with_data(self, post_id: str) -> Dict[str, Optional[str]]:
            """
            Fetches existing non-APPROVED variants (DRAFT or REJECTED).
            Returns a mapping of: {platform_name: error_message_or_None}
            """
            existing_variants = await self.variant_repo.get_by_post_id(post_id)
            if not existing_variants:
                return {}

            return {
                (v.platform.value if hasattr(v.platform, "value") else str(v.platform)).lower(): v.error_message
                for v in existing_variants
                if v.status != VariantStatus.APPROVED
            }



    async def _generate_text_variants(
            self, 
            source_text: str, 
            non_approved_targets: Optional[Dict[str, Optional[str]]] = None,
            approved_targets: Optional[Dict[str, Optional[str]]] = None
        ) -> List[GeneratedVariant]:
            """
            Dispatches generation requests to LLMService:
            - Skips execution if all variants are already APPROVED.
            - Calls generate_variants (initial run) if both approved and non_approved targets are empty.
            - Calls regenerate_variants (targeted run) if non_approved_targets contains platforms to retry/correct.
            """
            try:
                approved = approved_targets or {}
                non_approved = non_approved_targets or {}

                # CASE 1
                if approved and not non_approved:
                    logger.info(
                        f"⏩ All target platforms are already APPROVED ({list(approved.keys())}). "
                        f"Skipping generation/regeneration entirely."
                    )
                    return []

                # CASE 2: 
                if not non_approved and not approved:
                    logger.info("🚀 Triggering initial generation for all platforms...")
                    return await self.llm_service.generate_variants(
                        source_text=source_text
                    )

                # CAS 3:
                logger.info(f"🔄 Triggering targeted regeneration for platforms: {list(non_approved.keys())}")
                return await self.llm_service.regenerate_variants(
                    source_text=source_text,
                    target_feedbacks=non_approved
                )

            except Exception as e:
                logger.error(f"❌ Error during variant generation pipeline: {e}", exc_info=True)
                return []

    async def _persist_results(
        self, 
        post_id: str, 
        variants: List[GeneratedVariant]
    ) -> List[VariantResponse]:
        """
        Persists validated variants into public.variants using VariantRepository.
        """
        if not variants:
            logger.warning(f"⚠️ No variants to persist for Post ID: {post_id}")
            return []

        try:
            logger.info(f"💾 Persisting {len(variants)} variant(s) for Post ID: {post_id}...")
            persisted = await self.variant_repo.create_many(post_id=post_id, variants=variants)
            logger.info(f"✅ Successfully persisted {len(persisted)} variant(s) for Post ID: {post_id}")
            return persisted
        except Exception as e:
            logger.error(f"❌ Database error persisting variants for Post ID {post_id}: {e}", exc_info=True)
            raise e
