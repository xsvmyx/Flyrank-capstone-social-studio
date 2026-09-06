import time
from config.settings import logger
from app.database import supabase_admin
from config.config import QUEUE_NAME, VISIBILITY_TIMEOUT, MAX_RETRIES
from services.llm_service import GroqService
import asyncio

groq_service = GroqService()

async def process_job_simulation(payload: dict):
    """Simulates job execution that raises a runtime exception."""
    logger.info(f"⏳ Processing post ID: {payload.get('post_id')}...")
    await asyncio.sleep(2)
    raise RuntimeError("💥 CRITICAL ERROR: LLM API returned HTTP 500 Internal Server Error!")


async def run_worker():
    logger.info(f"=== Worker initialized in FAILURE SIMULATION mode on queue '{QUEUE_NAME}' ===")
    
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
                post_id = payload.get("post_id") or payload.get("id")
                logger.info(f"📥 Received Job #{msg_id} (Attempt {read_count}/{MAX_RETRIES})")

                
                if read_count >= MAX_RETRIES:
                    logger.error(f"❌ Job #{msg_id} exceeded maximum retries ({MAX_RETRIES}). Dropping and deleting job...")
                    supabase_admin.rpc("pgmq_delete", {"queue_name": QUEUE_NAME, "msg_id": msg_id}).execute()
                    continue


                # 3. Execute business logic 
                #await process_job_simulation(payload)
                #print(f"Processing post ID: {payload.get('post_id')}... (Simulated)") 
               # await asyncio.sleep(2)
                ############# AGENT CALL + IMAGE RESIZE + INSERTION INTO DB #############
                
                
                db_response = supabase_admin.table("raw_posts").select("*").eq("id", post_id).single().execute()
                raw_post_data = db_response.data

                if not raw_post_data or not raw_post_data.get("raw_content"):
                    raise ValueError(f"Post ID #{post_id} introuvable en base de données ou contenu vide.")

                

                text = await groq_service.call_llm(raw_post_data)

                logger.info(f"✅ LLM generated text for post ID #{post_id}: {text}")  



                supabase_admin.rpc("pgmq_delete", {"queue_name": QUEUE_NAME, "msg_id": msg_id}).execute()
                logger.info(f"✅ Job #{msg_id} completed successfully!")

        except Exception as e:
            logger.error(f"⚠️ Job execution failed: {e}")
            logger.info(f"🔁 Message hidden by PGMQ. Next retry attempt in {VISIBILITY_TIMEOUT} seconds...")

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