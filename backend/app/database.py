from supabase import create_client, Client
from config.config import SUPABASE_URL, SUPABASE_SERVICE_KEY, SUPABASE_ANON_KEY
from config.settings import logger


try:
    supabase_admin: Client = create_client(
        SUPABASE_URL,
        SUPABASE_SERVICE_KEY
    )
    logger.info("Supabase admin client initialized successfully")
except Exception as e:
    logger.error("Failed to initialize Supabase admin client: %s", e)
    raise



def get_user_db_client(access_token: str) -> Client:
    if not access_token or not access_token.strip():
        logger.error("Attempted to initialize user Supabase client with empty access token")
        raise ValueError("A valid JWT access token is required to create a user-scoped database client.")

    try:
        client: Client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)
        client.postgrest.auth(access_token)
        return client

    except Exception as e:
        logger.error("Failed to initialize user Supabase client with provided token: %s", e)
        raise RuntimeError(f"Could not create user-scoped database client: {str(e)}") from e