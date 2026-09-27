from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from supabase import create_client, Client
import os

security = HTTPBearer()

def get_supabase_admin() -> Client:
    """Service-role client. Bypass RLS. Only use for backend."""
    return create_client(
        os.getenv("SUPABASE_URL"),
        os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    )

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """
    Takes the JWT outside the Authorization header.
    Calls Supabase Auth to confirm the token is legit.
    Gives back the user (with id, email, etc.).
    """
    token = credentials.credentials
    supabase = get_supabase_admin()

    try:
        # This is the official way: Auth server validates the token
        user_response = supabase.auth.get_user(token)
        user = user_response.user
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token"
            )
        return user
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Could not validate credentials: {str(e)}"
        )
 
