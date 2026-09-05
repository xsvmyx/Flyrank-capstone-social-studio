from fastapi import APIRouter, Depends, HTTPException, status
from schemas.posts import NewRawPost
from supabase import Client
from dependencies import validate_token, get_db

router = APIRouter(prefix="/raw-posts", tags=["Raw Posts"])




@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_raw_post(
    post_data: NewRawPost,
    current_user=Depends(validate_token),
    db: Client = Depends(get_db),
):
    try:
        payload = {
            "title": post_data.title,
            "raw_content": post_data.raw_content,
            "image_url": post_data.image_url,
            "user_id": current_user.id,
        }

        
        response = db.table("raw_posts").insert(payload).execute()

        if not response.data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to create raw post",
            )

        return {
            "message": "Raw post created successfully",
            "data": response.data[0],
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create raw post: {str(e)}",
        )