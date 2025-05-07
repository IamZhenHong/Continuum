# routers/auth.py

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel
from src.services.auth.utils import create_jwt_token, verify_jwt_token, fetch_google_user_info, get_google_oauth_session
from typing import Optional
import os
from src.config.settings import settings
import logging
from src.schemas import AuthRequest
router = APIRouter()

# OAuth2 Password Bearer (used to secure routes requiring a JWT token)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")


# Pydantic Model for User Login (Google OAuth)
class UserLogin(BaseModel):
    username: str
    password: str

# 1. OAuth2 Login Route
@router.get("/login")
async def login():
    """
    Redirects user to Google OAuth2 login.
    """
    google_oauth, authorization_url = get_google_oauth_session()
    return {"authorization_url": authorization_url}

# 2. OAuth2 Callback Route (to fetch user info after successful login)
@router.post("/auth")
async def auth(authorization_request: AuthRequest):
    """
    This route handles the redirect after the user logs in with OAuth (Google).
    It fetches the user's info and returns a JWT token.
    """

    logging.info(f"Received Authorization Code: {authorization_request.code}")

    try:
        google_oauth, _ = get_google_oauth_session()
        logging.info("After getting Google OAuth session")
        user_info = fetch_google_user_info(google_oauth, authorization_request.code)
        logging.info("After fetching user info from Google")
        # You can customize this part to extract the needed information (e.g., email, name)
        user_data = {"email": user_info["email"], "name": user_info["name"]}
        logging.info("After extracting user data from Google")
        # Create JWT token
        token = create_jwt_token(user_data)
        logging.info("After creating JWT token")
        return {"access_token": token, "token_type": "bearer"}
    except Exception as e:
        raise HTTPException(status_code=400, detail="Invalid authentication response")

# 3. Route to get user profile (Secured by JWT token)
@router.get("/profile")
async def profile(token: str = Depends(oauth2_scheme)):
    """
    This is a protected route that requires a valid JWT token to access the user profile.
    """
    try:
        user = verify_jwt_token(token)
        return {"profile": user}
    except HTTPException:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

# 4. Helper functions to create and verify JWT token (inside utils.py)
