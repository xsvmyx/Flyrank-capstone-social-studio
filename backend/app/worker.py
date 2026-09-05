import time
from app.database import supabase_admin
from config.settings import logger

QUEUE_NAME = "raw_posts_jobs"

def start_worker():
    logger.info("=== Worker initialisé et en écoute sur la queue '%s' ===", QUEUE_NAME)
    
    while True:
        try:
            
            response = supabase_admin.rpc(
                "pgmq_read",
                {
                    "queue_name": QUEUE_NAME,
                    "vt": 30, 
                    "qty": 1
                }
            ).execute()

            messages = response.data

           
            if not messages:
                time.sleep(2)
                continue

            
            msg = messages[0]
            msg_id = msg["msg_id"]
            payload = msg["message"]

            print(f"\n[WORKER] 📥 Job reçu ! ID Message: {msg_id}")
            print(f"[WORKER] Payload contenu: {payload}")

            
            print("[WORKER] ⏳ Traitement en cours (simulation 5s)...")
            time.sleep(5)

            
            supabase_admin.rpc(
                "pgmq_delete",
                {
                    "queue_name": QUEUE_NAME,
                    "msg_id": msg_id
                }
            ).execute()

            print(f"[WORKER] ✅ Job {msg_id} traité et retiré de la queue avec succès !\n")

        except Exception as e:
            logger.error("Erreur dans la boucle du worker: %s", e)
            time.sleep(5)


if __name__ == "__main__":
    start_worker()