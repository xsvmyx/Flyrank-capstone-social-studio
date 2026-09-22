import asyncio
from config.settings import logger
from config.connections import supabase_admin
from config.settings import QUEUE_NAME, VISIBILITY_TIMEOUT, MAX_RETRIES 
from app.dependencies import create_orchestrator



orchestrator = create_orchestrator()


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
                payload = job["message"]

                logger.info(f"📥 Received Job #{msg_id} (Attempt {read_count}/{MAX_RETRIES})")

   
                if read_count >= MAX_RETRIES:
                    logger.error(f"❌ Job #{msg_id} exceeded maximum retries ({MAX_RETRIES}). Dropping job...")
                    #in the future we should mark it as the post as failed.

                    supabase_admin.rpc("pgmq_delete", {"queue_name": QUEUE_NAME, "msg_id": msg_id}).execute()
                    continue

                
                   
                await orchestrator.execute_job(payload=payload)
                


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
# MORE GROQ AGENTS
# job failure handling 