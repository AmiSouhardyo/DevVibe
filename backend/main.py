"""
Main FastAPI application.
Exposes endpoints for profile fetching, SQLite caching, Vibe Check compatibility,
and the AI Recruiter / Interview Coach chatbot.
Mounts the frontend static dashboard.
"""

import os
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Optional

from .database import init_db
from .github_service import get_developer_profile, GITHUB_TOKEN
from .vibe_check import calculate_compatibility
from .chatbot import generate_codebase_response, generate_interview_prep

app = FastAPI(
    title="GitHub Developer Portfolio & Vibe Check API",
    description="Professional developer dashboard with SQLite caching, streak calculation, and Tech Stack Compatibility scoring.",
    version="1.0.0"
)

# Enable CORS for local testing
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize database tables on startup
@app.on_event("startup")
def startup_event():
    init_db()

# Request Models
class VibeCheckRequest(BaseModel):
    username: str
    job_description: str

class ChatAskRequest(BaseModel):
    username: str
    question: str

class ChatInterviewRequest(BaseModel):
    username: str
    job_description: str

# Endpoints
@app.get("/api/health")
def health_check():
    return {
        "status": "healthy",
        "github_token_configured": bool(GITHUB_TOKEN),
        "rate_limit_mode": "Authenticated (5,000 req/hr)" if GITHUB_TOKEN else "Public (60 req/hr - Local SQLite Caching Active)"
    }

@app.get("/api/profile/{username}")
async def get_profile(username: str, force_refresh: bool = Query(False)):
    try:
        profile_data = await get_developer_profile(username, force_refresh=force_refresh)
        return profile_data
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=429, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/vibe-check")
def vibe_check(req: VibeCheckRequest):
    if not req.username:
        raise HTTPException(status_code=400, detail="Username is required.")
    return calculate_compatibility(req.username, req.job_description)

@app.post("/api/chat/ask")
def chat_ask(req: ChatAskRequest):
    if not req.username or not req.question:
        raise HTTPException(status_code=400, detail="Username and question are required.")
    return generate_codebase_response(req.username, req.question)

@app.post("/api/chat/interview")
def chat_interview(req: ChatInterviewRequest):
    if not req.username or not req.job_description:
        raise HTTPException(status_code=400, detail="Username and job description are required.")
    return generate_interview_prep(req.username, req.job_description)

# Mount frontend static directory
frontend_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "frontend")
if os.path.exists(frontend_dir):
    app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="frontend")
