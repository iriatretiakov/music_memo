import os
import base64
import httpx
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from database import get_db
import models
import urllib.parse
from spotify import ensure_valid_token

router = APIRouter(prefix="/auth", tags=["auth"])

SPOTIFY_CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
SPOTIFY_CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")
SPOTIFY_REDIRECT_URI = os.getenv("SPOTIFY_REDIRECT_URI")

@router.get("/login")
def login():
    scope = "user-read-private user-read-email user-library-read user-read-currently-playing"
    params = {
        "response_type": "code",
        "client_id": SPOTIFY_CLIENT_ID,
        "scope": scope,
        "redirect_uri": SPOTIFY_REDIRECT_URI,
    }
    query_params = urllib.parse.urlencode(params)
    auth_url = f"https://accounts.spotify.com/authorize?{query_params}"
    return RedirectResponse(auth_url)

@router.get("/callback")
async def callback(code: str = Query(None), db: Session = Depends(get_db)):
    if not code:
        raise HTTPException(status_code=400, detail="Missing code")

    auth_header = base64.b64encode(f"{SPOTIFY_CLIENT_ID}:{SPOTIFY_CLIENT_SECRET}".encode()).decode()
    async with httpx.AsyncClient() as client:
        token_res = await client.post(
            "https://accounts.spotify.com/api/token",
            data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": SPOTIFY_REDIRECT_URI,
            },
            headers={"Authorization": f"Basic {auth_header}"},
        )
        
        if token_res.status_code != 200:
            raise HTTPException(status_code=400, detail="Failed to get tokens")
            
        tokens = token_res.json()
        access_token = tokens["access_token"]
        refresh_token = tokens["refresh_token"]
        expires_in = tokens["expires_in"]
        expires_at = datetime.now() + timedelta(seconds=expires_in)

        user_res = await client.get(
            "https://api.spotify.com/v1/me",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        user_data = user_res.json()
        spotify_id = user_data["id"]

        user = db.query(models.User).filter(models.User.spotify_id == spotify_id).first()
        if not user:
            user = models.User(spotify_id=spotify_id)
            db.add(user)
        
        user.access_token = access_token
        user.refresh_token = refresh_token
        user.token_expires_at = expires_at
        
        db.commit()
        db.refresh(user)

    return {"message": "Authenticated successfully", "spotify_id": spotify_id}

@router.get("/me")
async def get_me(user_id: int, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    token = await ensure_valid_token(user, db)
    async with httpx.AsyncClient() as client:
        res = await client.get(
            "https://api.spotify.com/v1/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        return res.json()

@router.get("/me/current-track")
async def get_current_track(user_id: int, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    token = await ensure_valid_token(user, db)
    async with httpx.AsyncClient() as client:
        res = await client.get(
            "https://api.spotify.com/v1/me/player/currently-playing",
            headers={"Authorization": f"Bearer {token}"},
        )
        
        if res.status_code == 204 or not res.text:
            return {"message": "No track currently playing"}

        data = res.json()
        item = data.get("item")
        if not item:
            return {"message": "No track information available"}

        return {
            "track_id": item.get("id"),
            "track_name": item.get("name"),
            "artist_name": item.get("artists")[0].get("name") if item.get("artists") else "Unknown",
        }
