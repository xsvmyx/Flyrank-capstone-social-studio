
from fastapi import APIRouter, HTTPException, Depends, status
from supabase import Client
from app.dependencies import get_db
from schemas.variant_schemas import GenerateVariantRequest, GenerateVariantResponse , BatchJobResult , GenerateBatchVariantsRequest , GenerateBatchVariantsResponse , SocialPlatform
router = APIRouter(tags=["Generation"])



@router.post(
    "/posts/generate", 
    response_model=GenerateVariantResponse, 
    status_code=status.HTTP_202_ACCEPTED
)
async def generate_post_variant(
    body: GenerateVariantRequest,
    supabase: Client = Depends(get_db)
):
    """
    Triggers a variant generation job for a specific post and platform 
    by executing the enqueue_variant_job RPC in Supabase using payload data.
    """
    try:
        response = supabase.rpc(
            "enqueue_variant_job",
            {
                "p_post_id": body.post_id,
                "p_platform": body.platform.value
            }
        ).execute()

        msg_id = response.data

        if msg_id is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to enqueue variant job in PGMQ."
            )

        return GenerateVariantResponse(
            message=f"Post successfully enqueued for {body.platform.value} generation.",
            msg_id=msg_id,
            post_id=body.post_id,
            platform=body.platform
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Could not enqueue variant job: {str(e)}"
        )




@router.post(
    "/posts/generate-batch", 
    response_model=GenerateBatchVariantsResponse, 
    status_code=status.HTTP_202_ACCEPTED
)
async def generate_post_variants_batch(
    body: GenerateBatchVariantsRequest,
    supabase: Client = Depends(get_db)
):
    """
    Triggers multiple variant generation jobs for a specific post.
    If 'platforms' is empty or null, it enqueues jobs for all available SocialPlatforms.
    """
    try:
       
        target_platforms = body.platforms
        if not target_platforms:
            target_platforms = list(SocialPlatform)

        enqueued_results = []

        for platform in target_platforms:
            
            response = supabase.rpc(
                "enqueue_variant_job",
                {
                    "p_post_id": body.post_id,
                    "p_platform": platform.value
                }
            ).execute()

            msg_id = response.data

            if msg_id is None:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Failed to enqueue variant job for platform '{platform.value}'."
                )

            enqueued_results.append(
                BatchJobResult(platform=platform, msg_id=msg_id)
            )

        return GenerateBatchVariantsResponse(
            message=f"Successfully enqueued {len(enqueued_results)} variant generation job(s).",
            post_id=body.post_id,
            results=enqueued_results
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Could not enqueue batch variant jobs: {str(e)}"
        )


