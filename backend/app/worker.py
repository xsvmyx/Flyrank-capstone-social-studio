import asyncio
from config.settings import logger
from app.database import supabase_admin
from config.config import QUEUE_NAME, VISIBILITY_TIMEOUT, MAX_RETRIES
from services.llm_service import GroqService
from services.image_processing_service import ImageProcessor


SOCIAL_DIMENSIONS = {
    "instagram": (1080, 1080), 
    "linkedin": (1200, 627),    
    "twitter": (1200, 675),     
    "facebook": (1200, 630)     
}


async def process_post_job(payload: dict, image_processor: ImageProcessor):
    post_id = payload.get("post_id") or payload.get("id")
    if not post_id:
        raise ValueError("Invalid payload: missing 'post_id' or 'id'")

    logger.info(f"🔍 Fetching raw post data for Post ID: {post_id}")

    db_response = supabase_admin.table("raw_posts").select("*").eq("id", post_id).single().execute()
    raw_post = db_response.data

    if not raw_post:
        raise ValueError(f"Post ID #{post_id} not found in database.")

    user_id = raw_post.get("user_id")
    raw_media_path = raw_post.get("media_url") or raw_post.get("image_url")

    if not raw_media_path:
        raise ValueError(f"Post ID #{post_id} has no valid media/image path.")

    if not raw_media_path.startswith(("http://", "https://")):
        logger.info(f"🔑 Generating signed URL for storage path: {raw_media_path}")
        res = supabase_admin.storage.from_("post-media").create_signed_url(raw_media_path, 3600)
        

        if isinstance(res, dict):
            media_url = res.get("signedUrl") or res.get("signed_url")
        else:
            media_url = getattr(res, "signed_url", str(res))
    else:
        media_url = raw_media_path

    logger.info(f"🖼️ Resolved HTTP URL for download: {media_url}")


    processed_images = {}

    for platform, dimensions in SOCIAL_DIMENSIONS.items():
        logger.info(f"⏳ Resizing image for platform '{platform}' ({dimensions})...")
        
        resized_url = await image_processor.resize_and_upload(
            image_url=media_url,  # On passe l'URL HTTP résolue !
            dimensions=dimensions,
            user_id=user_id,
            platform_name=platform
        )
        processed_images[platform] = resized_url
        logger.info(f"✅ Image processed for {platform}: {resized_url}")

    return {
        "post_id": post_id,
        "processed_images": processed_images
    }


async def run_worker():
    logger.info(f"=== Worker active and listening on queue '{QUEUE_NAME}' ===")
    


    image_processor = ImageProcessor()

    while True:
        try:

            response = supabase_admin.rpc(
                "pgmq_read", 
                {"queue_name": QUEUE_NAME, "vt": VISIBILITY_TIMEOUT, "qty": 1}
            ).execute()
            
            jobs = response.data
            if jobs:
                job = jobs[0]
                msg_id = job["msg_id"]
                read_count = job["read_ct"]
                payload = job["message"]

                logger.info(f"📥 Received Job #{msg_id} (Attempt {read_count}/{MAX_RETRIES})")

   
                if read_count >= MAX_RETRIES:
                    logger.error(f"❌ Job #{msg_id} exceeded maximum retries ({MAX_RETRIES}). Dropping job...")
                    supabase_admin.rpc("pgmq_delete", {"queue_name": QUEUE_NAME, "msg_id": msg_id}).execute()
                    continue


                await process_post_job(payload, image_processor)


                supabase_admin.rpc("pgmq_delete", {"queue_name": QUEUE_NAME, "msg_id": msg_id}).execute()
                logger.info(f"🎉 Job #{msg_id} processed and deleted successfully!")

        except Exception as e:
            logger.error(f"⚠️ Job execution failed: {e}")
            logger.info(f"🔁 Job will retry in {VISIBILITY_TIMEOUT} seconds...")

        await asyncio.sleep(2)


if __name__ == "__main__":
    asyncio.run(run_worker())



#TO DO LIST :
# url scraping service
# DATABASE SERVICE FOR CLEANER USE
# MORE GROQ AGENTS
# Image resizing service
# Image bucketing service
# Better orchestration of the worker and the API