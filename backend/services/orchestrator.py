from typing import Dict, Any, Optional, List
from config.settings import logger
from services.llm_service import LLMService
from repositories.raw_post_repository import RawPostRepository
from schemas.posts_schemas import RawPostResponse
from schemas.variant_schemas import GeneratedVariant
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
        Orchestrates the complete job processing lifecycle.
        """
        post_id = payload.get("post_id")
        if not post_id:
            logger.error("❌ Job failed: Payload missing required key 'post_id'")
            raise ValueError("Payload missing required key 'post_id'")

        logger.info(f"⚙️ Executing job for Post ID: {post_id}")

        try:
            
            source_data = await self._fetch_and_prepare_source(post_id)
            content = source_data.get("raw_content")

            if not content or not content.strip():
                logger.warning(f"⚠️ Post ID {post_id} has empty content. Skipping generation.")
                return {"status": "skipped", "reason": "empty_content", "post_id": post_id}

            
            generated_variants: List[GeneratedVariant] = await self._generate_text_variants(content)

            if not generated_variants:
                logger.error(f"❌ Zero variants produced for Post ID: {post_id}")
                return {"status": "failed", "reason": "no_variants_generated", "post_id": post_id}

            logger.info(f"✨ Successfully generated {len(generated_variants)} text variant(s).")

            
            await self._persist_results(post_id=post_id, variants=generated_variants)

            return {"status": "success", "post_id": post_id}

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

    async def _generate_text_variants(self, source_text: str) -> List[GeneratedVariant]:
        """
        Calls LLMService to generate text variants dynamically across all agents.
        """
        try:
            return await self.llm_service.generate_all_variants(source_text)
        except Exception as e:
            logger.error(f"❌ Error during variant generation pipeline: {e}", exc_info=True)
            return []

    async def _persist_results(
        self,
        post_id: str,
        variants: List[GeneratedVariant]
    ) -> None:
        """
        Persists validated variants into the public.variants table using VariantRepository.
        """
        if not variants:
            logger.warning(f"⚠️ No variants generated to persist for Post ID: {post_id}")
            return

        try:
            logger.info(f"💾 Persisting {len(variants)} variant(s) for Post ID: {post_id}...")
            
            persisted_variants = await self.variant_repo.create_many(
                post_id=post_id, 
                variants=variants
            )
            
            logger.info(
                f"✅ Successfully persisted {len(persisted_variants)} variant(s) "
                f"for Post ID: {post_id}"
            )
        except Exception as e:
            logger.error(f"❌ Database error persisting variants for Post ID {post_id}: {e}", exc_info=True)
            raise e