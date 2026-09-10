from typing import Dict, Any, Optional, List
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
            Orchestrates the job processing lifecycle with concurrent execution 
            excluding already-approved variants.
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

                # 2. Fetch approved platforms to exclude from generation
                approved_platforms = await self._get_approved_platforms(post_id)
                if approved_platforms:
                    logger.info(f"📋 Found APPROVED platform(s) to skip: {approved_platforms}")

                # 3. Generate missing variants in parallel via LLMService
                generated_variants = await self._generate_text_variants(
                    source_text=content,
                    excluded_platforms=approved_platforms
                )

                if not generated_variants:
                    if approved_platforms:
                        logger.info(f"⏩ All variants are already APPROVED for Post ID: {post_id}. Nothing to do.")
                        return {"status": "skipped", "reason": "all_approved", "post_id": post_id}
                    
                    logger.error(f"❌ Zero variants produced for Post ID: {post_id}")
                    return {"status": "failed", "reason": "no_variants_generated", "post_id": post_id}

                logger.info(f"✨ Successfully generated {len(generated_variants)} new variant(s).")

                # 4. Persist results in database
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



    async def _get_approved_platforms(self, post_id: str) -> List[str]:
            """
            Fetches existing variants for a post_id and extracts the list
            of platform names that are already APPROVED.
            """
            existing_variants = await self.variant_repo.get_by_post_id(post_id)
            if not existing_variants:
                return []

            approved_platforms: List[str] = []
            for v in existing_variants:
                if v.status == VariantStatus.APPROVED:
                    platform_str = v.platform.value if hasattr(v.platform, "value") else str(v.platform)
                    approved_platforms.append(platform_str)

            return approved_platforms







    async def _generate_text_variants(
            self, 
            source_text: str, 
            excluded_platforms: Optional[List[str]] = None
        ) -> List[GeneratedVariant]:
            """
            Calls LLMService to generate text variants concurrently,
            excluding platforms that are already approved.
            """
            try:
                return await self.llm_service.generate_variants(
                    source_text=source_text,
                    excluded_platforms=excluded_platforms or []
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