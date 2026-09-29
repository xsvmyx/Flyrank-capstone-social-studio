
from fastapi import APIRouter, HTTPException, Depends, status
from supabase import Client
from app.dependencies import get_db
from schemas.variant_schemas import GenerateVariantRequest, GenerateVariantResponse

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





# @router.post(
#     "/posts/{post_id}/regenerate", 
#     response_model=RegeneratePostResponse, 
#     status_code=status.HTTP_202_ACCEPTED
# )
# async def regenerate_post(
#     post_id: str,
#     supabase: Client = Depends(get_db)
# ):
#     """
#     Triggers a re-generation job for an existing post by executing 
#     the enqueue_regeneration_job RPC in Supabase into 'background_jobs'.
#     """
#     try:
#         response = supabase.rpc(
#             "enqueue_regeneration_job",
#             {"p_post_id": post_id}
#         ).execute()

#         msg_id = response.data

#         if msg_id is None:
#             raise HTTPException(
#                 status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#                 detail="Failed to enqueue job in PGMQ."
#             )

#         return RegeneratePostResponse(
#             message="Post successfully enqueued for regeneration.",
#             msg_id=msg_id,
#             post_id=post_id
#         )

#     except HTTPException:
#         raise
#     except Exception as e:
#         raise HTTPException(
#             status_code=status.HTTP_400_BAD_REQUEST,
#             detail=f"Could not enqueue post: {str(e)}"
#         )