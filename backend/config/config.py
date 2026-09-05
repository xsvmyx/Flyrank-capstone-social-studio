
import os

from dotenv import load_dotenv
from groq import AsyncGroq

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

if not SUPABASE_URL or not SUPABASE_ANON_KEY:
    raise RuntimeError("auth.py: Missing Supabase Variables")


QUEUE_NAME = "raw_posts_jobs"
VISIBILITY_TIMEOUT = 20  
MAX_RETRIES = 3

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if not GROQ_API_KEY:
    raise RuntimeError("config.py: Missing GROQ_API_KEY")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

groq_client = AsyncGroq(api_key=os.getenv("GROQ_API_KEY"))