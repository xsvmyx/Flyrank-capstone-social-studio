from fastapi import APIRouter, HTTPException, Depends, status
from schemas.posts_schemas import RegeneratePostResponse
from supabase import Client
from app.dependencies import get_db


router = APIRouter(tags=["Regenerate"])




@router.post(
    "/posts/{post_id}/regenerate", 
    response_model=RegeneratePostResponse, 
    status_code=status.HTTP_202_ACCEPTED
)
async def regenerate_post(
    post_id: str,
    supabase: Client = Depends(get_db)
):
    """
    Triggers a re-generation job for an existing post by executing 
    the enqueue_regeneration_job RPC in Supabase.
    """
    try:
        response = supabase.rpc(
            "enqueue_regeneration_job",
            {"p_post_id": post_id}
        ).execute()

        msg_id = response.data

        if msg_id is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to enqueue job in PGMQ."
            )

        return RegeneratePostResponse(
            message="Post successfully enqueued for regeneration.",
            msg_id=msg_id,
            post_id=post_id
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Could not enqueue post: {str(e)}"
        )