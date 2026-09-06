from fastapi import APIRouter, HTTPException, status, Depends
import httpx
from config.config import SUPABASE_URL, SUPABASE_ANON_KEY
from schemas.login import LoginCredentials
from schemas.register import RegisterCredentials
from app.dependencies import validate_token


router = APIRouter(prefix="/api/auth", tags=["Auth"])





@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(credentials: RegisterCredentials):

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{SUPABASE_URL}/auth/v1/signup",
            headers={
                "apikey": SUPABASE_ANON_KEY,
                "Content-Type": "application/json"
            },
            json={
                "email": credentials.email,
                "password": credentials.password,
                "data": {
                    "first_name": credentials.first_name,
                    "last_name": credentials.last_name,
                }
            }
        )
        
        if response.status_code != 200:
            try:
                error_data = response.json()
                detail_msg = error_data.get("msg") or error_data.get("message") or response.text
            except Exception:
                detail_msg = response.text or "Erreur lors de l'inscription"
                
            raise HTTPException(
                status_code=response.status_code, 
                detail=detail_msg
            )
            
        data = response.json()
        return {
            "message": "Account Created Successfully",
            "user": data.get("user") or data
        }




@router.post("/login")
async def login(credentials: LoginCredentials):
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{SUPABASE_URL}/auth/v1/token?grant_type=password",
            headers={
                "apikey": SUPABASE_ANON_KEY,
                "Content-Type": "application/json"
            },
            json={
                "email": credentials.email,
                "password": credentials.password
            }
        )
        
        if response.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, 
                detail="Email ou mot de passe incorrect"
            )
            
        data = response.json()
        return {
            "access_token": data.get("access_token"),
            "token_type": "bearer",
            "user": data.get("user")
        }




@router.get("/me")
async def get_current_user_profile(
    current_user = Depends(validate_token)
):
    """
    Endpoint protégé qui confirme la connexion de l'utilisateur
    et retourne son identifiant ainsi qu'un message de bienvenue.
    """
    user_email = getattr(current_user, "email", "Utilisateur")
    
    return {
        "message": f"Bienvenue {user_email} ! Tu es correctement authentifié.",
        "user_id": current_user.id,
        "email": user_email,
        "status": "authenticated"
    }