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
    and business services (Image Processing, LLM Agents, Validation).
    """

    def __init__(
        self,
        raw_post_repo: RawPostRepository,
        llm_service: LLMService,
        variant_repo: VariantRepository
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
            raise ValueError("Payload missing required key 'post_id'")

        
        source_data = await self._fetch_and_prepare_source(post_id)
        content = source_data.get("raw_content")

        logger.info(f"⚙️ Executing job for Post ID: {post_id}")

        
        generated_variants: List[GeneratedVariant] = await self._generate_text_variants(content)

        logger.info(f"✨ Successfully generated {len(generated_variants)} text variant(s).")

        
        await self._persist_results(post_id=post_id, variants=generated_variants)

        return {"status": "success", "post_id": post_id}



    async def _fetch_and_prepare_source(self, post_id: str) -> Dict[str, Any]:
        """
        Fetches the source post from the database using RawPostRepository
        and returns a dictionary payload for the processing pipeline.
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
            Calls LLMService to generate text variants dynamically across all agents
            and logs the generated content for each platform.
            """
            # logger.info("🤖 Triggering text variant generation...")
            variants = await self.llm_service.generate_all_variants(source_text)

            return variants




    async def _process_media_variants(
        self,
        raw_media_path: str,
        user_id: str
    ) -> Dict[str, str]:
        """
        Handles downloading, multi-platform image resizing,
        and uploading of image variants.
        """
        ...

    async def _validate_constraints(
        self,
        text_variants: List[GeneratedVariant]
    ) -> Dict[str, bool]:
        """
        Verifies that each variant complies with required rules (length, hashtags, tone).
        """
        ...

    async def _persist_results(
            self,
            post_id: str,
            variants: List[GeneratedVariant]
        ) -> None:
            """
            Persists validated variants into the public.variants table using VariantRepository.
            Handles empty payload protection and logs insertion status.
            """
            if not variants:
                logger.warning(f"⚠️ No variants generated to persist for Post ID: {post_id}")
                return

            try:
                logger.info(f"💾 Persisting {len(variants)} variant(s) for Post ID: {post_id}...")
                
                # Execute batch upsert via the repository
                persisted_variants = await self.variant_repo.create_many(
                    post_id=post_id, 
                    variants=variants
                )
                
                logger.info(
                    f"✅ Successfully persisted {len(persisted_variants)} variant(s) "
                    f"to database for Post ID: {post_id}"
                )
            except Exception as e:
                logger.error(f"❌ Database error persisting variants for Post ID {post_id}: {e}")
                raise e