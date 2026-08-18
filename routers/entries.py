from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from database import get_db
import models
from typing import Optional

router = APIRouter(
    prefix="/entries",
    tags=["entries"],
)

class EntryCreate(BaseModel):
    user_id: int
    track_id: str
    track_name: str
    artist_name: str
    mood: str
    note: Optional[str] = None

@router.get("/")
def read_entries(user_id: int, limit: int = 20, db: Session = Depends(get_db)):
    return db.query(models.Entry)\
        .filter(models.Entry.user_id == user_id)\
        .order_by(models.Entry.created_at.desc())\
        .limit(max(1, min(limit, 100)))\
        .all()

@router.get("/track/{track_id}")
def read_track_entries(
    track_id: str,
    user_id: int,
    limit: int = 5,
    db: Session = Depends(get_db)
):
    return db.query(models.Entry)\
        .filter(models.Entry.user_id == user_id, models.Entry.track_id == track_id)\
        .order_by(models.Entry.created_at.desc())\
        .limit(max(1, min(limit, 50)))\
        .all()

@router.post("/")
def create_entry(entry: EntryCreate, db: Session = Depends(get_db)):
    # Verify user exists
    user = db.query(models.User).filter(models.User.id == entry.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    db_entry = models.Entry(
        user_id=entry.user_id,
        track_id=entry.track_id,
        track_name=entry.track_name,
        artist_name=entry.artist_name,
        mood=entry.mood,
        note=entry.note
    )
    db.add(db_entry)
    db.commit()
    db.refresh(db_entry)
    return db_entry

@router.delete("/{entry_id}")
def delete_entry(entry_id: int, user_id: int, db: Session = Depends(get_db)):
    db_entry = db.query(models.Entry)\
        .filter(models.Entry.id == entry_id, models.Entry.user_id == user_id)\
        .first()

    if not db_entry:
        raise HTTPException(status_code=404, detail="Entry not found")

    db.delete(db_entry)
    db.commit()
    return {"status": "deleted", "id": entry_id}
