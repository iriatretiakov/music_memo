import os
import base64
import httpx
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
import models

SPOTIFY_CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
SPOTIFY_CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")

async def ensure_valid_token(user: models.User, db: Session):
    # Check if token is expired (adding a 1-minute buffer for safety)
    if user.token_expires_at > datetime.now() + timedelta(minutes=1):
        return user.access_token

    # Token is expired, let's refresh it
    auth_header = base64.b64encode(f"{SPOTIFY_CLIENT_ID}:{SPOTIFY_CLIENT_SECRET}".encode()).decode()
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://accounts.spotify.com/api/token",
            data={
                "grant_type": "refresh_token",
                "refresh_token": user.refresh_token,
            },
            headers={"Authorization": f"Basic {auth_header}"},
        )
        
        if response.status_code != 200:
            # If refresh fails, you might want to force the user to re-login
            raise Exception("Failed to refresh Spotify token")
            
        data = response.json()
        
        # Update user in database
        user.access_token = data["access_token"]
        # Spotify may or may not return a new refresh token
        if "refresh_token" in data:
            user.refresh_token = data["refresh_token"]
            
        user.token_expires_at = datetime.now() + timedelta(seconds=data["expires_in"])
        
        db.commit()
        db.refresh(user)
        
        return user.access_token
