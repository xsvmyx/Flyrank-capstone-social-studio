import asyncio
from config.settings import logger
from config.connections import supabase_admin
from config.settings import QUEUE_NAME, VISIBILITY_TIMEOUT, MAX_RETRIES 
from app.dependencies import create_variant_generation_orchestrator,get_scraping_service

variant_generation_orchestrator = create_variant_generation_orchestrator()
scraping_service  = get_scraping_service()



async def handle_raw_post_created(payload: dict):
    await variant_generation_orchestrator.execute_job(payload=payload)


async def handle_scraping_requested(payload: dict):
    await scraping_service.execute_scraping(payload)



EVENT_HANDLERS = {
    "raw_post.created": handle_raw_post_created,
    "scraping.requested": handle_scraping_requested,
}




async def run_worker():
    logger.info(f"=== Worker active and listening on queue '{QUEUE_NAME}' ===")

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
                message_data = job["message"]

                
                event_type = message_data.get("event")
                payload = message_data.get("payload", message_data)

                logger.info(f"📥 Received Job #{msg_id} | Event: '{event_type}' (Attempt {read_count}/{MAX_RETRIES})")

                
                if read_count > MAX_RETRIES:
                    logger.error(f"❌ Job #{msg_id} ({event_type}) exceeded maximum retries. Dropping job...")
                    supabase_admin.rpc("pgmq_delete", {"queue_name": QUEUE_NAME, "msg_id": msg_id}).execute()
                    continue

                
                handler = EVENT_HANDLERS.get(event_type)

                if handler:
                    await handler(payload)
                    
                    
                    supabase_admin.rpc("pgmq_delete", {"queue_name": QUEUE_NAME, "msg_id": msg_id}).execute()
                    logger.info(f"🎉 Job #{msg_id} ({event_type}) processed and deleted successfully!")
                else:
                    logger.warning(f"⚠️ Unknown event type '{event_type}' for Job #{msg_id}. Dropping message...")
                    supabase_admin.rpc("pgmq_delete", {"queue_name": QUEUE_NAME, "msg_id": msg_id}).execute()

                
                continue

        except Exception as e:
            logger.error(f"⚠️ Job execution failed: {e}", exc_info=True)
            logger.info(f"🔁 Job will retry in {VISIBILITY_TIMEOUT} seconds...")

        # Pause uniquement si la file est vide ou après une erreur
        await asyncio.sleep(2)


if __name__ == "__main__":
    asyncio.run(run_worker())