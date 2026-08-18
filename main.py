import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import models
from database import engine
from routers import entries, auth

# Create database tables
models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="Music Memo API")

frontend_origin = os.getenv("FRONTEND_ORIGIN")
allowed_origins = (
    [origin.strip() for origin in frontend_origin.split(",") if origin.strip()]
    if frontend_origin
    else ["*"]
)

# Add CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=allowed_origins != ["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(entries.router)
app.include_router(auth.router)

@app.get("/")
def read_root():
    return {"message": "Welcome to Music Memo API"}

@app.get("/health")
def health():
    return {"status": "ok"}
