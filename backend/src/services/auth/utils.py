# utils.py

import os
from datetime import datetime, timedelta
import requests
from jose import JWTError, jwt
from requests_oauthlib import OAuth2Session
from dotenv import load_dotenv
from src.config.settings import settings
import secrets
# Load environment variables
load_dotenv()

CLIENT_ID = settings.GOOGLE_OAUTH.GOOGLE_CLIENT_ID
CLIENT_SECRET = settings.GOOGLE_OAUTH.GOOGLE_CLIENT_SECRET.get_secret_value()
REDIRECT_URI = settings.GOOGLE_OAUTH.REDIRECT_URI  # This is the URL where Google will redirect after login

JWT_SECRET_KEY = settings.JWT.JWT_SECRET_KEY.get_secret_value()
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_TIME = 3600  # 1 hour


SCOPES = [
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/userinfo.profile",
    "openid"
]


# OAuth2 helper functions
def get_google_oauth_session():
    """
    Returns an OAuth2 session and the authorization URL for Google login.
    """
    state = secrets.token_urlsafe(16)  # Or use any other method to generate a secure random string
    

    google_oauth = OAuth2Session(client_id=CLIENT_ID, redirect_uri=REDIRECT_URI, scope=SCOPES)
    authorization_url, state = google_oauth.authorization_url(
        "https://accounts.google.com/o/oauth2/auth",
        access_type="offline",
        prompt="select_account",
        state=state,
    )
    return google_oauth, authorization_url

import logging

def fetch_google_user_info(google_oauth: OAuth2Session, auth_code: str):
    """
    Fetches user information from Google after login.
    """
    try:
        # Log the authorization response being used for token exchange
        logging.info("Attempting to fetch token from Google using authorization code.")
        logging.debug(f"Authorization Response: {auth_code}")

        authorization_response = f"{REDIRECT_URI}?code={auth_code}"
        # Fetch the access token from Google's OAuth2 token endpoint
        token = google_oauth.fetch_token(
            "https://accounts.google.com/o/oauth2/token",
            authorization_response=authorization_response,
            client_secret=CLIENT_SECRET,
        )

        # Log the received token (or part of it, for security reasons)
        logging.info("Access token successfully fetched from Google.")
        logging.debug(f"Access token (partially masked): {token.get('access_token')[:5]}...")

        # Fetch user info from Google using the access token
        logging.info("Fetching user info from Google API.")
        user_info = google_oauth.get("https://www.googleapis.com/oauth2/v3/userinfo").json()

        # Log the user info response
        logging.info("User info fetched successfully from Google.")
        logging.debug(f"User Info: {user_info}")

        return user_info

    except Exception as e:
        # Log any errors that occur during the OAuth process
        logging.error(f"Error fetching Google user info: {e}")
        raise Exception(f"Error fetching Google user info: {e}")


# JWT helper functions
def create_jwt_token(data: dict):
    """
    Create a JWT token with user information.
    """
    payload = data.copy()
    payload["exp"] = datetime.utcnow() + timedelta(seconds=JWT_EXPIRATION_TIME)
    token = jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    return token

def verify_jwt_token(token: str):
    """
    Verifies the JWT token and returns the decoded user data.
    """
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        return payload
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
