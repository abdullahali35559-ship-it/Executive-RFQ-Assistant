import sys
import os

# Initialize sys.path to include the project root
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from dotenv import load_dotenv
# Load .env FIRST before any other imports
load_dotenv()

# Allow OAuth scope changes (Google sometimes adds openid/email automatically)
os.environ['OAUTHLIB_RELAX_TOKEN_SCOPE'] = '1'

from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, RedirectResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import asyncio
import time

# Performance Caching
calendar_cache = {} # {key: (timestamp, data)}
CACHE_TTL = 300 # 5 minutes

from typing import Dict, Optional, List
from sqlalchemy import desc, func, or_, text
from database.models import (
    Contact, Topic, Thread, Email, Attachment, DraftReply, 
    AuditLog, AssistantChat, AssistantConversation, Tag,
    FollowupTask
)
from config.database import SessionLocal, init_db
import msal
import json
from pathlib import Path
import secrets
import webbrowser
from datetime import datetime, timedelta, timezone

# --- Auth Imports ---
from fastapi.security import OAuth2PasswordRequestForm
from auth.user_manager import UserManager
from auth.session_manager import SessionManager
from auth.security import get_password_hash, verify_password, create_access_token
from auth.dependencies import get_current_user, oauth2_scheme
# --------------------

# Pydantic models for Assistant
class CreateConversationRequest(BaseModel):
    title: Optional[str] = "New Conversation"

class AssistantChatRequest(BaseModel):
    message: str
    context: Optional[str] = None
    conversation_id: Optional[int] = None

class CreateEventRequest(BaseModel):
    title: str
    start_time: str
    end_time: str
    description: Optional[str] = ""
    attendees: Optional[List[str]] = []
    provider: str = 'google'
    thread_id: Optional[str] = None

class TagCreate(BaseModel):
    name: str
    color: Optional[str] = "#6366f1"

class TagUpdate(BaseModel):
    name: Optional[str] = None
    color: Optional[str] = None

from models.pixtral_client import PixtralClient
import fitz # PyMuPDF
import hashlib
from fastapi import UploadFile, File as FastAPIFile
from config.prompts import (
    RFQ_AGENT_SYSTEM_PROMPT,
    DRAFT_EDITOR_SYSTEM_PROMPT,
    DRAFT_ENHANCEMENT_PROMPT_TEMPLATE
)

ASSISTANT_SYSTEM_PROMPT = """
You are the AI Assistant for the General Email Reply platform.
Your goal is to help users manage their business correspondence, categorize threads, and draft professional replies.

IMPORTANT: 
- If asked "Who are you?" or about your identity, respond that you are the "General Email Assistant AI". 
- NEVER mention "Pixtral", "Mistral", or any specific LLM model name. 
- Maintain a professional, helpful, and business-focused tone.
"""

from contextlib import asynccontextmanager
from agents.executive.assistant import ExecutiveAssistant

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize database tables on startup
    print("Initializing database...")
    init_db()
    print("Database initialized.")
    yield
    # Shutdown logic can go here

app = FastAPI(title="RFI API", lifespan=lifespan)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Mount storage for document previews
# Ensure the directory exists
storage_path = Path("storage")
if not storage_path.exists():
    storage_path.mkdir(exist_ok=True)
app.mount("/storage", StaticFiles(directory="storage"), name="storage")

# OAuth2 Config
from config.oauth_config import (
    CLIENT_ID, CLIENT_SECRET, TENANT_ID,
    REDIRECT_URI, SCOPES, TOKEN_FILE
)

# DEBUG: Print to verify values loaded
print("=" * 60)
print("DEBUG: OAuth Configuration")
print(f"CLIENT_ID: {CLIENT_ID}")
print(f"CLIENT_SECRET: {'*' * 10 if CLIENT_SECRET else 'None'}")
print(f"REDIRECT_URI: {REDIRECT_URI}")
print("=" * 60)
# Session storage (in-memory for simplicity)
oauth_sessions = {}
def get_msal_app():
    """Create MSAL confidential client"""
    return msal.ConfidentialClientApplication(
        CLIENT_ID,
        client_credential=CLIENT_SECRET,
        authority=f"https://login.microsoftonline.com/{TENANT_ID}"
    )
# Keep /dashboard redirect for compatibility
@app.get("/dashboard")
def dashboard_redirect():
    return FileResponse("ui/index.html")

@app.get("/")
def root_redirect():
    """Redirect root to dashboard"""
    return FileResponse("ui/index.html")

# ============================================
# AUTHENTICATION ROUTES
# ============================================

class UserRegister(BaseModel):
    username: str
    password: str
    email: Optional[str] = None
    role: Optional[str] = "user"

@app.post("/api/auth/register")
async def register(user_data: UserRegister):
    """Register a new user (JSON-based)"""
    um = UserManager()
    if um.get_user_by_username(user_data.username):
        raise HTTPException(status_code=400, detail="Username already exists")
    
    new_user = {
        "username": user_data.username,
        "password_hash": get_password_hash(user_data.password),
        "email": user_data.email,
        "role": user_data.role,
        "created_at": datetime.utcnow().isoformat()
    }
    
    if um.add_user(new_user):
        return {"success": True, "message": "User registered successfully"}
    else:
        raise HTTPException(status_code=500, detail="Failed to register user")

@app.post("/api/auth/login")
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    """Authenticate and get a JWT token"""
    um = UserManager()
    user = um.get_user_by_username(form_data.username)
    
    if not user or not verify_password(form_data.password, user["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token = create_access_token(data={"sub": user["username"]})
    
    # Store session
    sm = SessionManager()
    from auth.security import ACCESS_TOKEN_EXPIRE_MINUTES
    import time
    expires_at = time.time() + (ACCESS_TOKEN_EXPIRE_MINUTES * 60)
    sm.add_session(user["username"], access_token, expires_at)
    
    return {"access_token": access_token, "token_type": "bearer"}

@app.post("/api/auth/logout")
async def logout(current_user: dict = Depends(get_current_user), token: str = Depends(oauth2_scheme)):
    """Revoke the current session token"""
    sm = SessionManager()
    sm.revoke_session(token)
    return {"success": True, "message": "Logged out successfully"}

# ============================================
# TAGS & CATEGORIES API
# ============================================

@app.get("/api/tags")
async def get_tags(current_user: dict = Depends(get_current_user)):
    db = SessionLocal()
    try:
        tags = db.query(Tag).all()
        return {
            "success": True,
            "data": [{"id": t.id, "name": t.name, "color": t.color} for t in tags]
        }
    finally:
        db.close()

@app.post("/api/tags")
async def create_tag(tag_data: TagCreate, current_user: dict = Depends(get_current_user)):
    db = SessionLocal()
    try:
        # Check if already exists
        existing = db.query(Tag).filter(Tag.name == tag_data.name).first()
        if existing:
            raise HTTPException(status_code=400, detail="Tag already exists")
        
        new_tag = Tag(name=tag_data.name, color=tag_data.color)
        db.add(new_tag)
        db.commit()
        db.refresh(new_tag)
        return {
            "success": True,
            "data": {"id": new_tag.id, "name": new_tag.name, "color": new_tag.color}
        }
    finally:
        db.close()

@app.delete("/api/tags/{tag_id}")
async def delete_tag(tag_id: int, current_user: dict = Depends(get_current_user)):
    db = SessionLocal()
    try:
        tag = db.query(Tag).filter(Tag.id == tag_id).first()
        if not tag:
            raise HTTPException(status_code=404, detail="Tag not found")
        db.delete(tag)
        db.commit()
        return {"success": True}
    finally:
        db.close()

@app.post("/api/emails/{email_id}/tags/{tag_id}")
async def add_tag_to_email(email_id: int, tag_id: int, current_user: dict = Depends(get_current_user)):
    db = SessionLocal()
    try:
        email_obj = db.query(Email).filter(Email.id == email_id).first()
        tag = db.query(Tag).filter(Tag.id == tag_id).first()
        if not email_obj or not tag:
            raise HTTPException(status_code=404, detail="Email or Tag not found")
        
        if tag not in email_obj.tags:
            email_obj.tags.append(tag)
            
            # Sync to Thread (Topic)
            if email_obj.thread_id:
                thread = db.query(Thread).filter(Thread.thread_id == email_obj.thread_id).first()
                if thread and tag not in thread.tags:
                    thread.tags.append(tag)
            
            db.commit()
        return {"success": True}
    finally:
        db.close()

@app.delete("/api/emails/{email_id}/tags/{tag_id}")
async def remove_tag_from_email(email_id: int, tag_id: int, current_user: dict = Depends(get_current_user)):
    db = SessionLocal()
    try:
        email_obj = db.query(Email).filter(Email.id == email_id).first()
        tag = db.query(Tag).filter(Tag.id == tag_id).first()
        if not email_obj or not tag:
            raise HTTPException(status_code=404, detail="Email or Tag not found")
        
        if tag in email_obj.tags:
            email_obj.tags.remove(tag)
            
            # Sync removal from Thread (Topic)
            if email_obj.thread_id:
                thread = db.query(Thread).filter(Thread.thread_id == email_obj.thread_id).first()
                if thread and tag in thread.tags:
                    # Optional: only remove if no other emails in this thread have this tag
                    # For now, keep it simple and remove it.
                    thread.tags.remove(tag)
            
            db.commit()
        return {"success": True}
    finally:
        db.close()

@app.post("/api/threads/{thread_id}/tags/{tag_id}")
async def add_tag_to_thread(thread_id: int, tag_id: int, current_user: dict = Depends(get_current_user)):
    db = SessionLocal()
    try:
        thread = db.query(Thread).filter(Thread.id == thread_id).first()
        tag = db.query(Tag).filter(Tag.id == tag_id).first()
        if not thread or not tag:
            raise HTTPException(status_code=404, detail="Thread or Tag not found")
        if tag not in thread.tags:
            thread.tags.append(tag)
            db.commit()
        return {"success": True, "message": f"Tag '{tag.name}' added to thread"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

@app.delete("/api/threads/{thread_id}/tags/{tag_id}")
async def remove_tag_from_thread(thread_id: int, tag_id: int, current_user: dict = Depends(get_current_user)):
    db = SessionLocal()
    try:
        thread = db.query(Thread).filter(Thread.id == thread_id).first()
        tag = db.query(Tag).filter(Tag.id == tag_id).first()
        if not thread or not tag:
            raise HTTPException(status_code=404, detail="Thread or Tag not found")
        if tag in thread.tags:
            thread.tags.remove(tag)
            db.commit()
        return {"success": True, "message": f"Tag '{tag.name}' removed from thread"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

# ============================================
# OAUTH2 ROUTES (EXISTING)
# ============================================

@app.get("/api/oauth/login")
def oauth_login():
    """Initiate OAuth2 login flow"""
    
    # Generate state for CSRF protection
    state = secrets.token_urlsafe(32)
    oauth_sessions[state] = {'started': True}
    
    # Build MSAL app
    msal_app = get_msal_app()
    
    # MSAL 1.28.0+ automatically manages OIDC scopes ('openid', 'profile', 'offline_access')
    # Manually including them can cause 'ValueError: API does not accept frozenset...'
    active_scopes = [
        'https://graph.microsoft.com/Mail.ReadWrite',
        'https://graph.microsoft.com/Mail.Send',
        'https://graph.microsoft.com/Calendars.ReadWrite'
    ]
    
    # Get authorization URL
    auth_url = msal_app.get_authorization_request_url(
        active_scopes,
        state=state,
        redirect_uri=REDIRECT_URI
    )
    
    # Returning auth_url so frontend can open it
    return {
        "success": True, 
        "message": "OAuth URL generated",
        "auth_url": auth_url
    }

# Keeping redirect for backward compatibility
@app.get("/oauth/login")
def oauth_login_redirect():
    return RedirectResponse(url="/api/oauth/login")
@app.get("/oauth/callback")
def oauth_callback(code: str = None, state: str = None, error: str = None):
    """Handle OAuth2 callback"""
    
    # Check for errors
    if error:
        return HTMLResponse(
            content=f"""
            <html>
                <body style="font-family: Arial; padding: 40px; text-align: center;">
                    <h1 style="color: #d32f2f;">❌ Authentication Failed</h1>
                    <p>{error}</p>
                    <a href="/oauth/login" style="color: #0078d4;">Try Again</a>
                </body>
            </html>
            """,
            status_code=400
        )
    
    # Verify state (CSRF protection)
    # Note: For development, we'll skip strict validation due to auto-reload
    if state and state not in oauth_sessions:
        print(f"Warning: State {state} not in sessions. Continuing anyway (dev mode)...")
    
    # Exchange code for token
    msal_app = get_msal_app()
    
    result = msal_app.acquire_token_by_authorization_code(
        code,
        scopes=SCOPES,
        redirect_uri=REDIRECT_URI
    )
    
    if 'access_token' in result:
        # Save token
        token_data = {
            'access_token': result['access_token'],
            'refresh_token': result.get('refresh_token'),
            'expires_in': result.get('expires_in'),
            'token_type': result.get('token_type'),
            'scope': result.get('scope')
        }
        
        with open(TOKEN_FILE, 'w') as f:
            json.dump(token_data, f, indent=2)
        
        # Clean up session
        del oauth_sessions[state]
        
        return HTMLResponse(
            content="""
            <html>
                <head>
                    <title>Outlook Authentication Success</title>
                    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap" rel="stylesheet">
                    <style>
                        body {
                            font-family: 'Inter', sans-serif;
                            display: flex;
                            justify-content: center;
                            align-items: center;
                            height: 100vh;
                            margin: 0;
                            background-color: #f3f4f6;
                            color: #1f2937;
                        }
                        .container {
                            background: white;
                            padding: 40px;
                            border-radius: 12px;
                            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
                            text-align: center;
                            max-width: 450px;
                            width: 90%;
                        }
                        .icon-box {
                            width: 64px;
                            height: 64px;
                            background-color: #d1fae5;
                            border-radius: 50%;
                            display: flex;
                            align-items: center;
                            justify-content: center;
                            margin: 0 auto 20px;
                        }
                        .icon {
                            color: #10b981;
                            width: 32px;
                            height: 32px;
                        }
                        h1 { 
                            font-size: 24px;
                            font-weight: 700;
                            margin: 0 0 12px;
                            color: #111827;
                        }
                        p { 
                            margin: 0 0 28px;
                            color: #6b7280;
                            line-height: 1.5;
                        }
                        .btn {
                            background-color: #0078d4;
                            color: white;
                            padding: 12px 24px;
                            border: none;
                            border-radius: 6px;
                            font-weight: 600;
                            font-size: 14px;
                            text-decoration: none;
                            display: inline-block;
                            transition: background-color 0.2s;
                            cursor: pointer;
                        }
                        .btn:hover {
                            background-color: #006abc;
                        }
                    </style>
                </head>
                <body>
                    <div class="container">
                        <div class="icon-box">
                            <svg class="icon" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="3" d="M5 13l4 4L19 7"></path>
                            </svg>
                        </div>
                        <h1>Outlook Connected!</h1>
                        <p>Your Microsoft Outlook account has been successfully authenticated. The RFQ Agent is now securely connected.</p>
                        <button onclick="window.close();" class="btn">Close this window</button>
                    </div>
                </body>
            </html>
            """
        )
    else:
        error_desc = result.get('error_description', 'Token acquisition failed')
        return HTMLResponse(
            content=f"""
            <html>
                <body style="font-family: Arial; padding: 40px; text-align: center;">
                    <h1 style="color: #d32f2f;">❌ Token Error</h1>
                    <p>{error_desc}</p>
                    <a href="/oauth/login" style="color: #0078d4;">Try Again</a>
                </body>
            </html>
            """,
            status_code=400
        )
@app.get("/api/oauth/status")
@app.get("/oauth/status")
def oauth_status():
    """Check OAuth2 token status with live verification"""
    from agents.rfq_agent.outlook_graph import OutlookGraphFetcher
    
    if not TOKEN_FILE.exists():
        return {
            "success": True,
            "authenticated": False,
            "status": "disconnected",
            "message": "No token found. Please login first.",
            "login_url": "/oauth/login"
        }
    
    try:
        # Perform live verification
        outlook = OutlookGraphFetcher()
        is_connected = outlook.connect()
        
        with open(TOKEN_FILE, 'r') as f:
            token_data = json.load(f)
        
        return {
            "success": True,
            "authenticated": is_connected,
            "status": "connected" if is_connected else "unauthorized",
            "token_type": token_data.get('token_type'),
            "has_refresh_token": 'refresh_token' in token_data,
            "scopes": token_data.get('scope', '').split()
        }
    except Exception as e:
        print(f"Error checking OAuth status: {e}")
        return {
            "success": False,
            "authenticated": False,
            "status": "error",
            "error": str(e)
        }
@app.post("/oauth/refresh")
def oauth_refresh():
    """Refresh access token"""
    
    if not TOKEN_FILE.exists():
        raise HTTPException(status_code=404, detail="No token to refresh")
    
    with open(TOKEN_FILE, 'r') as f:
        token_data = json.load(f)
    
    if 'refresh_token' not in token_data:
        raise HTTPException(status_code=400, detail="No refresh token available")
    
    # Use MSAL to refresh
    msal_app = get_msal_app()
    
    # Scopes (using full Graph URIs for clarity and avoiding reserved names)
    # Must be a LIST. We OMIT 'openid', 'profile', 'offline_access' as MSAL handles them automatically.
    SCOPES = [
        'https://graph.microsoft.com/Mail.ReadWrite',
        'https://graph.microsoft.com/Mail.Send',
        'https://graph.microsoft.com/Calendars.ReadWrite'
    ]

    # Defense: ensure it's a list if imported by other modules
    if not isinstance(SCOPES, list):
        SCOPES = list(SCOPES)
    
    result = msal_app.acquire_token_by_refresh_token(
        token_data['refresh_token'],
        scopes=SCOPES
    )
    
    if 'access_token' in result:
        # Update token file
        new_token_data = {
            'access_token': result['access_token'],
            'refresh_token': result.get('refresh_token', token_data['refresh_token']),
            'expires_in': result.get('expires_in'),
            'token_type': result.get('token_type'),
            'scope': result.get('scope')
        }
        
        with open(TOKEN_FILE, 'w') as f:
            json.dump(new_token_data, f, indent=2)
        
        return {"status": "refreshed", "message": "Token refreshed successfully"}
    else:
        raise HTTPException(status_code=400, detail="Token refresh failed")

# ============================================
# GMAIL OAUTH2 ROUTES
# ============================================

from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials
from config.gmail_oauth_config import (
    GMAIL_CLIENT_ID,
    GMAIL_CLIENT_SECRET,
    GMAIL_REDIRECT_URI,
    GMAIL_TOKEN_FILE,
    GMAIL_SCOPES
)

def get_gmail_flow():
    """Create Gmail OAuth2 flow"""
    return Flow.from_client_config(
        {
            "web": {
                "client_id": GMAIL_CLIENT_ID,
                "client_secret": GMAIL_CLIENT_SECRET,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [GMAIL_REDIRECT_URI]
            }
        },
        scopes=GMAIL_SCOPES,
        redirect_uri=GMAIL_REDIRECT_URI
    )

@app.get("/api/gmail/oauth/login")
async def gmail_oauth_login():
    """Initiate Gmail OAuth2 flow"""
    try:
        flow = get_gmail_flow()
        
        # Generate authorization URL
        authorization_url, state = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='false',
            prompt='consent select_account'
        )
        
        # Store state
        oauth_sessions[f'gmail_{state}'] = state
        
        print(f"[OK] Gmail OAuth initiated")
        
        return {
            "success": True,
            "message": "OAuth URL generated",
            "auth_url": authorization_url
        }
    
    except Exception as e:
        print(f"[X] Gmail OAuth error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/gmail/oauth/login")
async def gmail_oauth_login_redirect():
    return RedirectResponse(url="/api/gmail/oauth/login")

@app.get("/api/gmail/oauth/callback")
@app.get("/gmail/oauth/callback")
async def gmail_oauth_callback(code: str = None, state: str = None, error: str = None):
    """Handle Gmail OAuth2 callback"""
    if error:
        return HTMLResponse(f"<h1>Error: {error}</h1>")
    
    if not code:
        return HTMLResponse("<h1>Error: No authorization code received</h1>")
    
    try:
        # Exchange code for tokens
        flow = get_gmail_flow()
        flow.fetch_token(code=code)
        
        credentials = flow.credentials
        
        print(f"DEBUG: Scopes granted by Google: {credentials.scopes}")
        
        # Save tokens
        token_data = {
            'token': credentials.token,
            'refresh_token': credentials.refresh_token,
            'token_uri': credentials.token_uri,
            'client_id': credentials.client_id,
            'client_secret': credentials.client_secret,
            'scopes': credentials.scopes
        }
        
        with open(GMAIL_TOKEN_FILE, 'w') as f:
            json.dump(token_data, f, indent=2)
        
        print(f"[OK] Gmail tokens saved to {GMAIL_TOKEN_FILE}")
        
        # Clean up session
        if f'gmail_{state}' in oauth_sessions:
            del oauth_sessions[f'gmail_{state}']
        
        return HTMLResponse(
            content="""
            <html>
                <head>
                    <title>Gmail Authentication Success</title>
                    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap" rel="stylesheet">
                    <style>
                        body {
                            font-family: 'Inter', sans-serif;
                            display: flex;
                            justify-content: center;
                            align-items: center;
                            height: 100vh;
                            margin: 0;
                            background-color: #f3f4f6;
                            color: #1f2937;
                        }
                        .container {
                            background: white;
                            padding: 40px;
                            border-radius: 12px;
                            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
                            text-align: center;
                            max-width: 450px;
                            width: 90%;
                        }
                        .icon-box {
                            width: 64px;
                            height: 64px;
                            background-color: #d1fae5;
                            border-radius: 50%;
                            display: flex;
                            align-items: center;
                            justify-content: center;
                            margin: 0 auto 20px;
                        }
                        .icon {
                            color: #10b981;
                            width: 32px;
                            height: 32px;
                        }
                        h1 { 
                            font-size: 24px;
                            font-weight: 700;
                            margin: 0 0 12px;
                            color: #111827;
                        }
                        p { 
                            margin: 0 0 28px;
                            color: #6b7280;
                            line-height: 1.5;
                        }
                        .btn {
                            background-color: #ea4335;
                            color: white;
                            padding: 12px 24px;
                            border: none;
                            border-radius: 6px;
                            font-weight: 600;
                            font-size: 14px;
                            text-decoration: none;
                            display: inline-block;
                            transition: background-color 0.2s;
                            cursor: pointer;
                        }
                        .btn:hover {
                            background-color: #d33828;
                        }
                    </style>
                </head>
                <body>
                    <div class="container">
                        <div class="icon-box">
                            <svg class="icon" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="3" d="M5 13l4 4L19 7"></path>
                            </svg>
                        </div>
                        <h1>Gmail Connected!</h1>
                        <p>Your Gmail account has been successfully authenticated. The RFQ Agent is now securely connected.</p>
                        <button onclick="window.close();" class="btn">Close this window</button>
                    </div>
                </body>
            </html>
            """
        )
    
    except Exception as e:
        print(f"[X] Gmail callback error: {e}")
        return HTMLResponse(f"<h1>Error: {str(e)}</h1>")

@app.get("/api/gmail/oauth/status")
@app.get("/gmail/oauth/status")
async def gmail_oauth_status():
    """Check Gmail OAuth2 status"""
    token_file = Path(GMAIL_TOKEN_FILE)
    
    if not token_file.exists():
        return {
            "authenticated": False,
            "message": "Not authenticated. Please visit /gmail/oauth/login"
        }
    
    try:
        with open(token_file, 'r') as f:
            token_data = json.load(f)
        
        return {
            "authenticated": True,
            "scopes": token_data.get('scopes', []),
            "has_refresh_token": bool(token_data.get('refresh_token'))
        }
    
    except Exception as e:
        return {
            "authenticated": False,
            "error": str(e)
        }

@app.post("/gmail/oauth/refresh")
async def gmail_oauth_refresh():
    """Refresh Gmail access token"""
    token_file = Path(GMAIL_TOKEN_FILE)
    
    if not token_file.exists():
        raise HTTPException(status_code=404, detail="No token file found")
    
    try:
        with open(token_file, 'r') as f:
            token_data = json.load(f)
        
        credentials = Credentials(
            token=token_data.get('token'),
            refresh_token=token_data.get('refresh_token'),
            token_uri=token_data.get('token_uri'),
            client_id=token_data.get('client_id'),
            client_secret=token_data.get('client_secret'),
            scopes=token_data.get('scopes')
        )
        
        # Refresh token
        from google.auth.transport.requests import Request as GoogleRequest
        credentials.refresh(GoogleRequest())
        
        # Save new token
        token_data['token'] = credentials.token
        with open(token_file, 'w') as f:
            json.dump(token_data, f, indent=2)
        
        return {
            "status": "success",
            "message": "Token refreshed successfully"
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ============================================
# DRAFT EMAIL MANAGEMENT API
# ===========================================

from database.connection import SessionLocal
from database.models import DraftReply as DraftEmail, Email, Thread as Tender, Attachment as Document, Contact
from agents.rfq_agent.outlook_graph import OutlookGraphFetcher
from agents.rfq_agent.gmail_api_client import GmailAPIFetcher
from sqlalchemy import desc, text

class DraftUpdate(BaseModel):
    subject: Optional[str] = None
    body: Optional[str] = None

class DraftEnhance(BaseModel):
    instructions: str

class DraftCreate(BaseModel):
    recipient: str
    thread_id: Optional[str] = None
    subject: str
    body: str
    draft_type: str = "RESPONSE"
    in_reply_to_email_id: Optional[str] = None



@app.get("/api/drafts")
async def get_drafts(tender_id: Optional[str] = None, current_user: dict = Depends(get_current_user)):
    """Get all draft emails, optionally filtered by tender_id"""
    db = SessionLocal()
    
    try:
        query = db.query(DraftEmail)
        
        if tender_id:
            query = query.filter(DraftEmail.tender_id == tender_id)
        
        query = query.filter(DraftEmail.status == 'DRAFT')
        query = query.order_by(desc(DraftEmail.created_at))
        
        drafts = query.all()
        
        return {
            "success": True,
            "count": len(drafts),
            "drafts": [
                {
                    "id": d.id,
                    "thread_id": d.thread_id,
                    "draft_type": d.draft_type,
                    "recipient": d.recipient,
                    "subject": d.subject,
                    "body": d.body,
                    "email_provider": d.email_provider,
                    "provider_draft_id": d.provider_draft_id,
                    "status": d.status,
                    "created_at": d.created_at.isoformat() if d.created_at else None,
                    "updated_at": d.updated_at.isoformat() if d.updated_at else None
                }
                for d in drafts
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

@app.get("/api/drafts/{draft_id}")
async def get_draft(draft_id: int, current_user: dict = Depends(get_current_user)):
    """Get a specific draft by ID"""
    db = SessionLocal()
    
    try:
        draft = db.query(DraftEmail).filter(DraftEmail.id == draft_id).first()
        
        if not draft:
            raise HTTPException(status_code=404, detail="Draft not found")
        
        return {
            "success": True,
            "data": {
                "id": draft.id,
                "thread_id": draft.thread_id,
                "draft_type": draft.draft_type,
                "recipient": draft.recipient,
                "subject": draft.subject,
                "body": draft.body,
                "email_provider": draft.email_provider,
                "provider_draft_id": draft.provider_draft_id,
                "status": draft.status,
                "created_at": draft.created_at.isoformat() if draft.created_at else None,
                "updated_at": draft.updated_at.isoformat() if draft.updated_at else None
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

@app.post("/api/drafts")
async def create_draft(draft_data: DraftCreate, current_user: dict = Depends(get_current_user)):
    """Create a new draft email"""
    db = SessionLocal()
    
    try:
        # Detect provider from tender source
        provider = 'outlook'  # Default
        # Optional: Link to thread
        if draft_data.thread_id:
            thread = db.query(Thread).filter(Thread.thread_id == draft_data.thread_id).first()
            if thread and thread.source:
                if 'gmail' in thread.source.lower():
                    provider = 'gmail'
                elif 'outlook' in thread.source.lower():
                    provider = 'outlook'
        
        # Create draft in the appropriate provider
        if provider == 'gmail':
            fetcher = GmailAPIFetcher()
            if not fetcher.connect():
                raise HTTPException(status_code=500, detail="Failed to connect to Gmail API")
            result = fetcher.create_draft(
                to=draft_data.recipient,
                subject=draft_data.subject,
                body=draft_data.body,
                in_reply_to=draft_data.in_reply_to_email_id
            )
        else:
            fetcher = OutlookGraphFetcher()
            result = fetcher.create_draft(
                to=draft_data.recipient,
                subject=draft_data.subject,
                body=draft_data.body,
                in_reply_to=draft_data.in_reply_to_email_id
            )
        
        if not result.get('success'):
            raise HTTPException(status_code=500, detail=result.get('error', f'Failed to create {provider} draft'))
        
        # Save to database
        draft = DraftEmail(
            thread_id=draft_data.thread_id,
            draft_type=draft_data.draft_type,
            recipient=draft_data.recipient,
            subject=draft_data.subject,
            body=draft_data.body,
            email_provider=provider,
            provider_draft_id=result['draft_id'],
            status='DRAFT',
            in_reply_to_email_id=draft_data.in_reply_to_email_id
        )
        
        db.add(draft)
        db.commit()
        db.refresh(draft)
        
        return {
            "success": True,
            "message": "Draft created successfully",
            "draft_id": draft.id,
            "provider_draft_id": result['draft_id'],
            "provider": provider
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

@app.put("/api/drafts/{draft_id}")
async def update_draft(draft_id: int, draft_update: DraftUpdate, current_user: dict = Depends(get_current_user)):
    """Update an existing draft email"""
    db = SessionLocal()
    
    try:
        # Get draft from database
        draft = db.query(DraftEmail).filter(DraftEmail.id == draft_id).first()
        
        if not draft:
            raise HTTPException(status_code=404, detail="Draft not found")
        
        # Detect provider
        provider = draft.email_provider or 'outlook'
        
        if provider == 'gmail':
            fetcher = GmailAPIFetcher()
            if not fetcher.connect():
                raise HTTPException(status_code=500, detail="Failed to connect to Gmail API")
            result = fetcher.update_draft(
                draft_id=draft.provider_draft_id,
                subject=draft_update.subject,
                body=draft_update.body
            )
        else:
            fetcher = OutlookGraphFetcher()
            result = fetcher.update_draft(
                draft_id=draft.provider_draft_id,
                subject=draft_update.subject,
                body=draft_update.body
            )
        
        if not result.get('success'):
            raise HTTPException(status_code=500, detail=result.get('error', f'Failed to update {provider} draft'))
        
        # Update database
        if draft_update.subject is not None:
            draft.subject = draft_update.subject
        
        if draft_update.body is not None:
            draft.body = draft_update.body
        
        draft.updated_at = datetime.utcnow()
        
        db.commit()
        
        return {
            "success": True,
            "message": "Draft updated successfully",
            "draft_id": draft.id
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

@app.post("/api/drafts/{draft_id}/send")
async def send_draft(draft_id: int, current_user: dict = Depends(get_current_user)):
    """Send a draft email"""
    db = SessionLocal()
    
    try:
        # Get draft from database
        draft = db.query(DraftEmail).filter(DraftEmail.id == draft_id).first()
        
        if not draft:
            raise HTTPException(status_code=404, detail="Draft not found")
        
        if draft.status != 'DRAFT':
            raise HTTPException(status_code=400, detail=f"Draft already {draft.status}")
        
        # Detect provider
        provider = draft.email_provider or 'outlook'
        
        if provider == 'gmail':
            fetcher = GmailAPIFetcher()
            if not fetcher.connect():
                raise HTTPException(status_code=500, detail="Failed to connect to Gmail API")
            result = fetcher.send_draft(draft.provider_draft_id)
        else:
            fetcher = OutlookGraphFetcher()
            result = fetcher.send_draft(draft.provider_draft_id)
        
        if not result.get('success'):
            raise HTTPException(status_code=500, detail=result.get('error', f'Failed to send {provider} draft'))
        
        # Update database
        draft.status = 'SENT'
        draft.sent_at = datetime.utcnow()
        
        db.commit()
        
        return {
            "success": True,
            "message": "Draft sent successfully",
            "draft_id": draft.id,
            "sent_at": draft.sent_at.isoformat()
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

@app.post("/api/drafts/{draft_id}/enhance")
async def enhance_draft(draft_id: int, enhancement: DraftEnhance, current_user: dict = Depends(get_current_user)):
    """Enhance a draft email using AI based on user instructions"""
    db = SessionLocal()
    try:
        # Get draft from database
        draft = db.query(DraftEmail).filter(DraftEmail.id == draft_id).first()
        if not draft:
            raise HTTPException(status_code=404, detail="Draft not found")

        # Prepare prompt
        prompt = DRAFT_ENHANCEMENT_PROMPT_TEMPLATE.format(
            current_subject=draft.subject,
            current_body=draft.body,
            instructions=enhancement.instructions
        )

        # Call AI with concise system prompt and zero temperature for speed
        ai_client = PixtralClient()
        result = ai_client.generate(
            system_prompt=DRAFT_EDITOR_SYSTEM_PROMPT,
            user_prompt=prompt,
            temperature=0.0
        )

        if not result or result.get('error'):
             raise HTTPException(status_code=500, detail=result.get('error', "AI enhancement failed"))

        return {
            "success": True,
            "subject": result.get('subject', draft.subject),
            "body": result.get('body', draft.body),
            "reasoning": result.get('reasoning', "Draft enhanced based on instructions")
        }
    except Exception as e:
        print(f"Error enhancing draft: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

@app.delete("/api/drafts/{draft_id}")
async def delete_draft(draft_id: int, current_user: dict = Depends(get_current_user)):
    """Delete a draft email"""
    db = SessionLocal()
    
    try:
        # Get draft from database
        draft = db.query(DraftEmail).filter(DraftEmail.id == draft_id).first()
        
        if not draft:
            raise HTTPException(status_code=404, detail="Draft not found")
        
        # Detect provider
        provider = draft.email_provider or 'outlook'
        
        if provider == 'gmail':
            fetcher = GmailAPIFetcher()
            if fetcher.connect():
                fetcher.delete_draft(draft.provider_draft_id)
        else:
            fetcher = OutlookGraphFetcher()
            fetcher.delete_draft(draft.provider_draft_id)
        
        # Mark as deleted in DB regardless of provider deletion outcome
        draft.status = 'DELETED'
        db.commit()
        
        return {
            "success": True,
            "message": "Draft deleted successfully",
            "draft_id": draft.id
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

@app.get("/api/session-summary")
async def get_session_summary(from_time: str, to_time: str, current_user: dict = Depends(get_current_user)):
    """Get emails processed within a given time window, with tender & document details."""
    db = SessionLocal()
    try:
        from datetime import datetime as dt, timezone
        # Parse ISO datetime strings from query params (e.g. 2026-03-06T09:00:00.000Z)
        try:
            _from = from_time.replace('Z', '+00:00')
            _to = to_time.replace('Z', '+00:00')
            start = dt.fromisoformat(_from)
            end = dt.fromisoformat(_to)
            
            # Database stores naive UTC, convert and strip timezone if present
            if start.tzinfo:
                start = start.astimezone(timezone.utc).replace(tzinfo=None)
            if end.tzinfo:
                end = end.astimezone(timezone.utc).replace(tzinfo=None)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid datetime format. Use ISO format")

        # Fetch emails processed in this window
        emails = db.query(Email).filter(
            Email.processed == True,
            Email.created_at >= start,
            Email.created_at <= end
        ).order_by(Email.created_at.desc()).limit(100).all()

        # For each email, get attachment count and thread subject
        results = []
        for e in emails:
            att_count = db.query(func.count(Attachment.id)).filter(
                Attachment.thread_id == e.thread_id
            ).scalar() if e.thread_id else 0

            results.append({
                "email_id": e.id,
                "subject": e.subject,
                "sender": e.sender,
                "thread_id": e.thread_id,
                "received_at": e.received_at.isoformat() if e.received_at else None,
                "processed_at": e.created_at.isoformat() if e.created_at else None,
                "att_count": att_count,
            })

        return {
            "success": True,
            "count": len(results),
            "from_time": from_time,
            "to_time": to_time,
            "data": results
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

@app.get("/api/emails")
async def get_emails(thread_id: Optional[str] = None, status: Optional[str] = None, include_all: bool = True, current_user: dict = Depends(get_current_user)):
    """Get all emails, optionally filtered"""
    db = SessionLocal()
    
    try:
        query = db.query(Email)
        
        if thread_id:
            query = query.filter(Email.thread_id == thread_id)
        
        if status:
            if status == "processed":
                query = query.filter(Email.processed == True)
            elif status == "unprocessed":
                query = query.filter(Email.processed == False)
            elif status == "actionable":
                query = query.filter(Email.is_junk == False)
            elif status == "junk":
                query = query.filter(Email.is_junk == True)
        
        emails = query.order_by(desc(Email.id)).all()
        
        # Get active drafts
        drafts = db.query(DraftReply).filter(DraftReply.status == 'DRAFT').all()
        draft_map = {d.in_reply_to_email_id: d.id for d in drafts if d.in_reply_to_email_id}
        
        # Get attachment counts
        att_counts = {}
        thread_ids = [e.thread_id for e in emails if e.thread_id]
        if thread_ids:
            counts = db.query(Attachment.thread_id, func.count(Attachment.id)).filter(
                Attachment.thread_id.in_(thread_ids)
            ).group_by(Attachment.thread_id).all()
            att_counts = {tid: count for tid, count in counts}

        return {
            "success": True,
            "count": len(emails),
            "data": [
                {
                    "id": e.id,
                    "email_id": e.email_id,
                    "thread_id": e.thread_id,
                    "subject": e.subject,
                    "sender": e.sender,
                    "from": e.sender,
                    "date": e.received_at.isoformat() if e.received_at else None,
                    "body": e.body[:200] if e.body else None,
                    "received_at": e.received_at.isoformat() if e.received_at else None,
                    "is_junk": e.is_junk,
                    "processed": e.processed,
                    "attachments": att_counts.get(e.thread_id, 0),
                    "tags": [{"id": t.id, "name": t.name, "color": t.color} for t in e.tags],
                    "tags_suggested": e.tags_suggested or [],
                    "status": "junk" if e.is_junk else "processed" if e.processed else "unprocessed",
                    "detection_confidence": e.detection_confidence,
                    "has_draft": e.email_id in draft_map,
                    "draft_id": draft_map.get(e.email_id)
                }
                for e in emails
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

@app.get("/api/emails/{email_id}")
async def get_email(email_id: int, current_user: dict = Depends(get_current_user)):
    """Get full details for a specific email"""
    db = SessionLocal()
    try:
        email = db.query(Email).filter(Email.id == email_id).first()
        if not email:
            raise HTTPException(status_code=404, detail="Email not found")
            
        return {
            "success": True,
            "data": {
                "id": email.id,
                "email_id": email.email_id,
                "thread_id": email.thread_id,
                "subject": email.subject,
                "sender": email.sender,
                "body": email.body,
                "received_at": email.received_at.isoformat() if email.received_at else None,
                "is_junk": email.is_junk,
                "processed": email.processed,
                "tags": [{"id": t.id, "name": t.name, "color": t.color} for t in email.tags],
                "tags_suggested": email.tags_suggested or []
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

@app.post("/api/emails/{email_id}/archive")
async def archive_email(email_id: int, current_user: dict = Depends(get_current_user)):
    """Mark an email as processed/archived"""
    db = SessionLocal()
    try:
        email = db.query(Email).filter(Email.id == email_id).first()
        if not email:
            raise HTTPException(status_code=404, detail="Email not found")
        email.processed = True
        db.commit()
        return {"success": True, "message": "Email archived successfully"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

@app.post("/api/emails/{email_id}/confirm_tags")
async def confirm_email_tags(email_id: int, current_user: dict = Depends(get_current_user)):
    """Convert AI suggestions into active tags"""
    db = SessionLocal()
    try:
        email = db.query(Email).filter(Email.id == email_id).first()
        if not email:
            raise HTTPException(status_code=404, detail="Email not found")
        
        if not email.tags_suggested:
            return {"success": True, "message": "No suggestions to confirm"}
            
        # Find existing tags that match suggestions
        matching_tags = db.query(Tag).filter(Tag.name.in_(email.tags_suggested)).all()
        
        added_count = 0
        for tag in matching_tags:
            if tag not in email.tags:
                email.tags.append(tag)
                added_count += 1
        
        # Clear suggestions after confirmation
        email.tags_suggested = []
        db.commit()
        
        return {"success": True, "message": f"Applied {added_count} tags", "tags": [{"id": t.id, "name": t.name, "color": t.color} for t in email.tags]}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

@app.get("/api/attachments/{att_id}")
async def get_attachment(att_id: int, current_user: dict = Depends(get_current_user)):
    """Get metadata for a specific attachment"""
    db = SessionLocal()
    try:
        att = db.query(Attachment).filter(Attachment.id == att_id).first()
        if not att:
            raise HTTPException(status_code=404, detail="Attachment not found")
        rel_path = att.file_path
        view_url = ""
        
        if rel_path.startswith('URL:'):
            view_url = rel_path.replace('URL:', '')
        else:
            if rel_path.startswith('./'): rel_path = rel_path[2:]
            if rel_path.startswith('storage/'): rel_path = rel_path[len('storage/'):]
            rel_path = rel_path.replace('\\', '/')
            view_url = f"/storage/{rel_path}"
        
        return {
            "success": True,
            "data": {
                "id": att.id,
                "filename": att.filename,
                "file_path": att.file_path,
                "view_url": view_url,
                "doc_type": att.doc_type,
                "thread_id": att.thread_id,
                "summary": att.summary,
                "uploaded_at": att.uploaded_at.isoformat() if att.uploaded_at else None
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

@app.get("/api/attachments")
async def list_all_attachments(current_user: dict = Depends(get_current_user)):
    """List all attachments with thread and sender info for grouping"""
    db = SessionLocal()
    try:
        # Join Attachment with Thread to get sender and subject info
        results = db.query(Attachment, Thread).outerjoin(Thread, Attachment.thread_id == Thread.thread_id).order_by(desc(Attachment.uploaded_at)).all()
        
        data = []
        for att, thread in results:
            rel_path = att.file_path
            view_url = ""
            
            if rel_path.startswith('URL:'):
                view_url = rel_path.replace('URL:', '')
            else:
                if rel_path.startswith('./'): rel_path = rel_path[2:]
                if rel_path.startswith('storage/'): rel_path = rel_path[len('storage/'):]
                rel_path = rel_path.replace('\\', '/')
                view_url = f"/storage/{rel_path}"
                
            data.append({
                "id": att.id,
                "name": att.filename,
                "filename": att.filename,
                "file_path": att.file_path,  # Essential for frontend handleFileAction
                "file_type": att.doc_type,
                "type": att.doc_type,
                "thread_id": att.thread_id,
                "thread": att.thread_id,
                "size": f"{round(att.file_size_bytes / 1024, 1)} KB" if att.file_size_bytes else "0 KB",
                "received_at": att.uploaded_at.isoformat() if att.uploaded_at else None,
                "sender_email": thread.source_email if thread else "Unknown",
                "sender_name": thread.contact_name if thread else "Unknown",
                "subject": thread.subject if thread else "No Subject",
                "view_url": view_url,
                "summary": att.summary,
                "tags": [] 
            })
        return {
            "success": True,
            "count": len(data),
            "data": data
        }
    except Exception as e:
        print(f"Error listing attachments: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

@app.delete("/api/attachments/{att_id}")
async def delete_attachment(att_id: int, current_user: dict = Depends(get_current_user)):
    """Delete an attachment from DB and storage"""
    db = SessionLocal()
    try:
        att = db.query(Attachment).filter(Attachment.id == att_id).first()
        if not att:
            raise HTTPException(status_code=404, detail="Attachment not found")
            
        try:
            file_path = Path(att.file_path)
            if file_path.exists(): file_path.unlink()
        except: pass
            
        db.delete(att)
        db.commit()
        return {"success": True, "message": "Attachment deleted successfully"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

@app.post("/api/attachments/upload")
async def upload_attachment(file: UploadFile = FastAPIFile(...), current_user: dict = Depends(get_current_user)):
    """Upload a new attachment"""
    db = SessionLocal()
    try:
        upload_dir = Path("storage/manual_uploads")
        upload_dir.mkdir(parents=True, exist_ok=True)
        content = await file.read()
        file_hash = hashlib.sha256(content).hexdigest()
        filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{file.filename}"
        file_path = upload_dir / filename
        with open(file_path, "wb") as f: f.write(content)
            
        new_att = Attachment(
            filename=filename,
            original_filename=file.filename,
            file_path=str(file_path),
            file_hash=file_hash,
            file_size_bytes=len(content),
            doc_type='Manual Upload',
            uploaded_at=datetime.utcnow(),
            thread_id='N/A'
        )
        db.add(new_att)
        db.commit()
        return {"success": True, "attachment_id": new_att.id}
    except Exception as e:
        db.rollback()
        print(f"Upload error: {e}")
        return {"success": False, "error": str(e)}
    finally:
        db.close()

@app.post("/api/contacts")
async def add_contact(contact_data: dict, current_user: dict = Depends(get_current_user)):
    """Add a new contact"""
    db = SessionLocal()
    try:
        new_contact = Contact(
            name=contact_data.get("name"),
            email=contact_data.get("email"),
            phone=contact_data.get("phone"),
            company=contact_data.get("company"),
            job_title=contact_data.get("job_title"),
            notes=contact_data.get("notes")
        )
        db.add(new_contact)
        db.commit()
        db.refresh(new_contact)
        return {"success": True, "data": {"id": new_contact.id}}
    except Exception as e:
        db.rollback()
        print(f"Error adding contact: {e}")
        return {"success": False, "error": str(e)}
    finally:
        db.close()

@app.get("/api/dashboard/stats")
async def get_dashboard_stats(current_user: dict = Depends(get_current_user)):
    """Get aggregate statistics for the dashboard"""
    db = SessionLocal()
    try:
        active_threads = db.query(Thread).count()
        total_emails = db.query(Email).count()
        total_contacts = db.query(Contact).count()
        pending_replies = db.query(DraftEmail).count()
        unprocessed_emails = db.query(Email).filter(Email.processed == False).count()
        calendar_events = 0

        # 6. Calendar Events (Today) - With Caching
        cache_key = "dashboard_calendar_count"
        now_ts = time.time()
        if cache_key in calendar_cache:
            ts, val = calendar_cache[cache_key]
            if now_ts - ts < CACHE_TTL:
                calendar_events = val
            else: del calendar_cache[cache_key]
        
        if cache_key not in calendar_cache:
            try:
                from agents.executive.scheduler import GoogleCalendarClient, OutlookCalendarClient
                
                def get_g_count_sync():
                    try:
                        g = GoogleCalendarClient()
                        if g.connect(): return len(g.get_upcoming_events(days=1))
                    except: pass
                    return 0

                def get_o_count_sync():
                    try:
                        o = OutlookCalendarClient()
                        if o.connect(): return len(o.get_upcoming_events(days=1))
                    except: pass
                    return 0

                g_count, o_count = await asyncio.gather(
                    asyncio.to_thread(get_g_count_sync),
                    asyncio.to_thread(get_o_count_sync)
                )
                calendar_events = g_count + o_count
                calendar_cache[cache_key] = (now_ts, calendar_events)
            except Exception as ce:
                print(f"Calendar stats error: {ce}")

        return {
            "success": True,
            "data": {
                "activeTenders": active_threads,
                "unreadEmails": total_emails,
                "unprocessedEmails": unprocessed_emails,
                "pendingRFIs": pending_replies,
                "totalClients": total_contacts,
                "calendarEvents": calendar_events
            }
        }
    except Exception as e:
        print(f"Error in dashboard stats: {e}")
        return {
            "success": False,
            "error": str(e),
            "data": {
                "activeTenders": 0,
                "unreadEmails": 0,
                "pendingRFIs": 0,
                "totalClients": 0,
                "calendarEvents": 0
            }
        }
    finally:
        db.close()

# Connectivity status cache
STATUS_CACHE = {
    "data": None,
    "last_check": 0
}
import time

@app.get("/api/status")
async def get_system_status(current_user: dict = Depends(get_current_user)):
    """Check connectivity to various system components (cached for 60s)"""
    global STATUS_CACHE
    
    # Return cached data if less than 60 seconds old
    if STATUS_CACHE["data"] and (time.time() - STATUS_CACHE["last_check"] < 60):
        return STATUS_CACHE["data"]
        
    status = {
        "database": False,
        "gmail": False,
        "outlook": "disconnected",
        "llm": False
    }
    
    # Check Database
    try:
        from sqlalchemy import text, func, or_, desc
        db_check = SessionLocal()
        db_check.execute(text("SELECT 1"))
        db_check.close()
        status["database"] = True
    except:
        pass
    
    # Check Outlook - Live verification
    try:
        TOKEN_FILE = ".outlook_oauth_token.json"
        outlook = OutlookGraphFetcher()
        if outlook.connect():
            status["outlook"] = "connected"
        elif Path(TOKEN_FILE).exists():
            status["outlook"] = "unauthorized"
        else:
            status["outlook"] = "disconnected"
    except Exception as e:
        status["outlook"] = "error"
        
    # Check Gmail
    GMAIL_TOKEN_FILE = ".gmail_oauth_token.json"
    if Path(GMAIL_TOKEN_FILE).exists():
        status["gmail"] = True
        
    # Check LLM
    try:
        from models.pixtral_client import PixtralClient
        llm_check = PixtralClient()
        if llm_check.test_connection():
            status["llm"] = True
    except:
        pass
    
    STATUS_CACHE["data"] = status
    STATUS_CACHE["last_check"] = time.time()
    
    return status

from fastapi import BackgroundTasks
from scripts.process_emails import process_email_batch

@app.post("/api/documents/{doc_id}/toggle-correct")
async def toggle_document_correct(doc_id: int, current_user: dict = Depends(get_current_user)):
    """Toggle the correctness status of a document"""
    db = SessionLocal()
    try:
        doc = db.query(Document).filter(Document.id == doc_id).first()
        if not doc:
            raise HTTPException(status_code=404, detail="Document not found")
        
        doc.is_correct = not doc.is_correct
        if not doc.is_correct:
            doc.rejection_reason = "Marked incorrect by user"
        else:
            doc.rejection_reason = None
            
        db.commit()
        return {"success": True, "is_correct": doc.is_correct}
    finally:
        db.close()

@app.post("/api/drafts/{draft_id}/attachments")
async def upload_draft_attachment(draft_id: int, file: UploadFile = FastAPIFile(...), current_user: dict = Depends(get_current_user)):
    """Upload a file and attach it to an existing draft email"""
    db = SessionLocal()
    try:
        draft = db.query(DraftEmail).filter(DraftEmail.id == draft_id, DraftEmail.status == 'DRAFT').first()
        if not draft:
            raise HTTPException(status_code=404, detail="Draft not found or already sent")
        
        content = await file.read()
        filename = file.filename
        
        # Initialize appropriate manager
        from agents.rfq_agent.gmail_api_client import GmailAPIFetcher
        from agents.rfq_agent.outlook_graph import OutlookGraphFetcher
        
        result = {"success": False, "error": "Provider connection failed"}
        
        if draft.email_provider == 'gmail':
            fetcher = GmailAPIFetcher()
            if fetcher.connect():
                result = fetcher.add_attachment_to_draft(draft.provider_draft_id, filename, content)
        elif draft.email_provider == 'outlook':
            fetcher = OutlookGraphFetcher()
            if fetcher.connect():
                result = fetcher.add_attachment_to_draft(draft.provider_draft_id, filename, content)
        
        # CRITICAL: Gmail draft IDs change when updated. We MUST save the new one.
        if result.get('success') and result.get('draft_id'):
            if result['draft_id'] != draft.provider_draft_id:
                print(f"DEBUG: Updating draft {draft_id} provider ID from {draft.provider_draft_id} to {result['draft_id']}")
                draft.provider_draft_id = result['draft_id']
                db.commit()
                
        return result
    except Exception as e:
        print(f"Error uploading draft attachment: {e}")
        return {"success": False, "error": str(e)}
    finally:
        db.close()

# Global state for sync progress
sync_progress = {"status": "Idle", "current": 0, "total": 0, "active": False}

@app.get("/api/agent/status")
async def get_agent_status(current_user: dict = Depends(get_current_user)):
    """Return the current processing status of the agent"""
    return sync_progress

@app.post("/api/process-emails")
async def trigger_email_processing(current_user: dict = Depends(get_current_user)):
    """Trigger the email processing agent and track progress"""
    global sync_progress
    try:
        sync_progress["active"] = True
        sync_progress["status"] = "Scanning Inboxes..."
        
        from agents.rfq_agent.email_fetcher import EmailFetcher
        # If agent.py is missing/hidden, we handle gracefully
        try:
            from agents.rfq_agent.agent import RFQAgent
            agent = RFQAgent()
        except ImportError:
            # Fallback or Mock
            agent = None
            print("Warning: RFQAgent not found, using manual extraction")
            
        from agents.rfq_agent.cloud_link_detector import CloudLinkDetector
        link_detector = CloudLinkDetector()
        db = SessionLocal()
        
        # We need to use a thread for the long-running process to not block status polling
        # But for simpler implementation, we just update as we go.
        # Note: In a production async app, this would be a background task.
        
        # Fetch from both Gmail and Outlook
        emails = []
        # Fetch from both Gmail and Outlook, keeping track of which fetcher fetched which email
        emails = []
        provider_fetchers = {}
        for provider in ['gmail', 'outlook']:
            try:
                fetcher = EmailFetcher(provider=provider)
                provider_fetchers[provider] = fetcher
                provider_emails = fetcher.fetch_emails(limit=25)
                if provider_emails:
                    for pe in provider_emails:
                        pe['_provider'] = provider # Tag for marking read later
                    emails.extend(provider_emails)
            except Exception as e:
                print(f"Error fetching from {provider}: {e}")

        if not emails:
            sync_progress["active"] = False
            sync_progress["status"] = "Idle"
            return {"success": True, "processed": 0}

        sync_progress["total"] = len(emails)
        processed_count = 0
        
        for i, email in enumerate(emails):
            sync_progress["current"] = i + 1
            sync_progress["percentage"] = int((sync_progress["current"] / sync_progress["total"]) * 100)
            subject_snip = email.get('subject', 'No Subject')[:25]
            sync_progress["status"] = f"Analyzing {i+1}/{len(emails)}: {subject_snip}..."
            
            try:
                print(f"\n---> STARTING ANALYSIS: {subject_snip} ({i+1}/{len(emails)})")
                if agent:
                    agent.process_incoming_email(email)
                print(f"---> ANALYSIS COMPLETE. Now attempting to mark as read...")
                
                # Mark as read across providers
                provider = email.get('_provider')
                msg_id_for_api = email.get('email_id')
                
                if provider and msg_id_for_api:
                    print(f"  [DEBUG] Attempting to mark as read: {msg_id_for_api} ({provider})")
                    if provider in provider_fetchers:
                        success = provider_fetchers[provider].mark_as_read(msg_id_for_api)
                        if success:
                            processed_count += 1
                        else:
                            print(f"  [!] Failed to mark {msg_id_for_api} as read via fetcher.")
                else:
                    print(f"  [!] Missing provider or ID for marking read: {provider}, {msg_id_for_api}")
                
                # Manual Cloud Link Extraction for the UI
                cloud_links = link_detector.detect_links(email.get('body', ''))
                if cloud_links:
                    # Find the thread created for this email
                    from database.models import Thread as TenderTable
                    thread = db.query(TenderTable).filter(TenderTable.source_email == email.get('sender')).order_by(desc(TenderTable.created_at)).first()
                    
                    if thread:
                        for link in cloud_links:
                            # Avoid duplicates
                            exists = db.query(Attachment).filter(
                                Attachment.thread_id == thread.thread_id,
                                Attachment.file_path == f"URL:{link['url']}"
                            ).first()
                            
                            if not exists:
                                # Classify safety
                                safety_rating = link_detector.classify_link_safety(link['url'])
                                safety_tag = f"[{safety_rating}] " if safety_rating != "TRUSTED" else ""
                                if safety_rating == "SUSPICIOUS":
                                    safety_tag = "[SUSPICIOUS ⚠️] "
                                
                                new_att = Attachment(
                                    thread_id=thread.thread_id,
                                    filename=f"{safety_tag}{link['provider'].value.title()} Link",
                                    file_path=f"URL:{link['url']}",
                                    doc_type="LINK",
                                    file_size_bytes=0,
                                    uploaded_at=datetime.utcnow(),
                                    summary=f"Safety: {safety_rating}. Cloud link extracted from email body."
                                )
                                db.add(new_att)
                                print(f"Registered {safety_rating} cloud link: {link['url']}")
                        db.commit()
                
                processed_count += 1
            except Exception as inner_e:
                print(f"Error processing email {i+1}: {inner_e}")

        sync_progress["status"] = "Syncing Dashboard..."
        sync_progress["active"] = False
        return {"success": True, "processed": processed_count}
    except Exception as e:
        sync_progress["active"] = False
        sync_progress["status"] = f"Error: {str(e)}"
        print(f"Global Sync Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if 'db' in locals():
            db.close()

@app.get("/api/agent/status/legacy")
async def get_agent_status_legacy(current_user: dict = Depends(get_current_user)):
    """Get the latest progress from the AuditLog table"""
    db = SessionLocal()
    try:
        from sqlalchemy import desc
        # Ensure comparison is naive-to-naive
        now_naive = datetime.now(timezone.utc).replace(tzinfo=None)
        one_hour_ago = now_naive - timedelta(hours=1)
        
        logs = db.query(AuditLog).filter(
            AuditLog.action.like("PROGRESS:%"),
            AuditLog.timestamp >= one_hour_ago
        ).order_by(desc(AuditLog.timestamp)).limit(20).all()
        
        # Determine if active by looking at the last few minutes
        is_active = False
        debug_info = {}
        if logs:
            # Strip tzinfo from DB timestamp just in case it's aware
            last_timestamp = logs[0].timestamp
            if last_timestamp.tzinfo:
                last_timestamp = last_timestamp.replace(tzinfo=None)
                
            time_diff = (now_naive - last_timestamp).total_seconds()
            
            # Cases for is_active:
            # 1. Check if the last log indicates completion, failure, or being finished
            last_action_lower = logs[0].action.lower()
            batch_done = any(kw in last_action_lower for kw in ["complete", "finished", "failed"])
            
            # 2. Determine if active
            if not batch_done and time_diff < 120:
                is_active = True
            elif not batch_done and time_diff < 1800:
                # If it's a "ongoing" log (not complete) and within the last 30 mins
                is_active = True
            else:
                is_active = False
        
        return {
            "success": True,
            "is_active": is_active,
            "latest_logs": [
                {
                    "action": log.action.replace("PROGRESS: ", ""),
                    "details": log.details,
                    "timestamp": log.timestamp.isoformat()
                }
                for log in logs
            ]
        }
    except Exception as e:
        print(f"Error fetching agent status: {e}")
        return {"success": False, "error": str(e)}
    finally:
        db.close()

@app.get("/api/activity")
async def get_activity(limit: int = 10):
    """Get recent system activity"""
    # Mock activity for now
    return {
        "success": True,
        "activities": [
            {
                "title": "System Check",
                "meta": "All systems operational",
                "badge": "Online",
                "type": "success"
            }
        ]
    }

@app.get("/api/contacts/{contact_id}")
async def get_contact_api(contact_id: int, current_user: dict = Depends(get_current_user)):
    """Get a specific contact by ID"""
    db = SessionLocal()
    try:
        contact = db.query(Contact).filter(Contact.id == contact_id).first()
        if not contact:
            raise HTTPException(status_code=404, detail="Contact not found")
        return {
            "success": True,
            "data": {
                "id": contact.id,
                "name": contact.contact_name,
                "email": contact.email_domain,
                "first_seen": contact.first_seen.isoformat() if contact.first_seen else None,
                "last_contact": contact.last_contact.isoformat() if contact.last_contact else None,
                "threads": len(contact.threads) if contact.threads else 0
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

@app.get("/api/contacts")
async def get_contacts_api(current_user: dict = Depends(get_current_user)):
    """Get all contacts"""
    db = SessionLocal()
    try:
        contacts = db.query(Contact).all()
        return {
            "success": True,
            "count": len(contacts),
            "data": [
                {
                    "id": c.id,
                    "name": c.contact_name,
                    "email": c.email_domain,
                    "threads": len(c.threads) if c.threads else 0,
                    "status": "active"
                }
                for c in contacts
            ]
        }
    finally:
        db.close()

@app.get("/api/threads")
async def get_threads(status: Optional[str] = None, current_user: dict = Depends(get_current_user)):
    """Get all threads with optional status filter"""
    db = SessionLocal()
    try:
        query = db.query(Thread)
        if status:
            query = query.filter(Thread.status == status)
        threads = query.order_by(desc(Thread.updated_at)).all()
        
        results = []
        for t in threads:
            count = db.query(Attachment).filter(Attachment.thread_id == t.thread_id).count()
            
            # Fetch latest meeting suggestion
            latest_email = db.query(Email).filter(
                Email.thread_id == t.thread_id,
                Email.meta_data.isnot(None)
            ).order_by(Email.received_at.desc()).first()
            
            meeting_suggestion = None
            if latest_email and latest_email.meta_data:
                meeting_suggestion = latest_email.meta_data.get('meeting_suggestion')
            
            # Force booked status if thread itself is marked as booked
            if t.status == 'MEETING_BOOKED' and meeting_suggestion:
                meeting_suggestion['booked'] = True

            # Get sender email from first message
            first_msg = db.query(Email).filter(Email.thread_id == t.thread_id).order_by(Email.received_at.asc()).first()
            sender_email = first_msg.sender if first_msg else ""

            results.append({
                "id": t.id,
                "thread_id": t.thread_id,
                "status": t.status.lower() if t.status else "pending",
                "contact": t.contact_name,
                "sender_email": sender_email,
                "subject": t.subject or t.topic_name,
                "date": t.created_at.isoformat() if t.created_at else None,
                "contact_name": t.contact_name,
                "topic_name": t.topic_name,
                "created_at": t.created_at.isoformat() if t.created_at else None,
                "updated_at": t.updated_at.isoformat() if t.updated_at else None,
                "attachments": count,
                "tags": [{"id": tag.id, "name": tag.name, "color": tag.color} for tag in t.tags],
                "meeting_suggestion": meeting_suggestion
            })
            
        return {
            "success": True,
            "data": results
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

@app.get("/api/threads/{thread_id}")
async def get_single_thread(thread_id: str, current_user: dict = Depends(get_current_user)):
    """Get details for a specific thread"""
    db = SessionLocal()
    try:
        thread = db.query(Thread).filter(Thread.thread_id == thread_id).first()
        if not thread:
            raise HTTPException(status_code=404, detail="Thread not found")
        return {
            "id": thread.id,
            "thread_id": thread.thread_id,
            "status": thread.status,
            "contact_name": thread.contact_name,
            "topic_name": thread.topic_name,
            "subject": thread.subject,
            "created_at": thread.created_at.isoformat() if thread.created_at else None
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

@app.get("/api/attachments/{att_id}")
async def get_attachment(att_id: int, current_user: dict = Depends(get_current_user)):
    """Get metadata for a specific attachment"""
    db = SessionLocal()
    try:
        att = db.query(Attachment).filter(Attachment.id == att_id).first()
        if not att:
            raise HTTPException(status_code=404, detail="Attachment not found")
        rel_path = att.file_path
        if rel_path.startswith('./'): rel_path = rel_path[2:]
        if rel_path.startswith('storage/'): rel_path = rel_path[len('storage/'):]
        rel_path = rel_path.replace('\\', '/')
        
        return {
            "success": True,
            "data": {
                "id": att.id,
                "filename": att.filename,
                "view_url": f"/storage/{rel_path}",
                "doc_type": att.doc_type,
                "thread_id": att.thread_id,
                "summary": att.summary,
                "uploaded_at": att.uploaded_at.isoformat() if att.uploaded_at else None
            }
        }
    finally:
        db.close()

@app.get("/api/threads/{thread_id}/attachments")
async def get_thread_attachments(thread_id: str, current_user: dict = Depends(get_current_user)):
    """Get attachments associated with a thread"""
    db = SessionLocal()
    try:
        if not thread_id or thread_id in ('undefined', 'all'):
            docs = db.query(Attachment).order_by(desc(Attachment.uploaded_at)).all()
        else:
            docs = db.query(Attachment).filter(Attachment.thread_id == thread_id).all()
            
        email_info = {}
        thread_ids = list(set([d.thread_id for d in docs if d.thread_id]))
        if thread_ids:
            emails = db.query(Email).filter(Email.thread_id.in_(thread_ids)).all()
            for e in emails:
                if e.thread_id not in email_info:
                    email_info[e.thread_id] = {"subject": e.subject, "sender": e.sender}

        results = []
        for d in docs:
            t = db.query(Thread).filter(Thread.thread_id == d.thread_id).first()
            results.append({
                "id": d.id,
                "name": d.original_filename or d.filename,
                "type": d.doc_type or 'Document',
                "thread": d.thread_id or 'N/A',
                "thread_updated_at": t.updated_at.isoformat() if t and t.updated_at else d.uploaded_at.isoformat(),
                "source_email": email_info.get(d.thread_id, {}).get('subject', 'N/A'),
                "source_sender": email_info.get(d.thread_id, {}).get('sender', 'N/A'),
                "summary": d.summary,
                "size": f"{d.file_size_bytes / 1024:.1f} KB" if d.file_size_bytes else "0 KB",
                "date": d.uploaded_at.isoformat() if d.uploaded_at else datetime.utcnow().isoformat(),
            })
            
        # Inject empty threads if fetching all
        if not thread_id or thread_id in ('undefined', 'all'):
            all_threads = db.query(Thread).all()
            existing_threads = {d.thread_id for d in docs if d.thread_id}
            for t in all_threads:
                if t.thread_id and t.thread_id not in existing_threads:
                    results.append({
                        "id": f"empty_{t.id}",
                        "name": "No attachments",
                        "type": "none",
                        "thread": t.thread_id,
                        "thread_updated_at": t.updated_at.isoformat() if t.updated_at else t.created_at.isoformat(),
                        "source_email": t.subject or t.topic_name,
                        "source_sender": t.contact_name or "Unknown",
                        "size": "0 KB",
                        "date": t.created_at.isoformat() if t.created_at else datetime.utcnow().isoformat(),
                    })
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

@app.post("/api/meetings/book-suggested")
async def book_suggested_meeting(request: Dict, current_user: dict = Depends(get_current_user)):
    """Book a meeting suggested by AI for a specific thread"""
    thread_id = request.get('thread_id')
    provider = request.get('provider', 'google') # Default or detect from email
    
    db = SessionLocal()
    try:
        # 1. Find the latest email for this thread with meeting_suggestion meta
        from database.models import Email, Thread
        from agents.executive.scheduler import GoogleCalendarClient, OutlookCalendarClient

        email = db.query(Email).filter(
            Email.thread_id == thread_id,
            Email.meta_data.isnot(None)
        ).order_by(Email.received_at.desc()).first()
        
        if not email or not email.meta_data or 'meeting_suggestion' not in email.meta_data:
            raise HTTPException(status_code=404, detail="No meeting suggestion found for this thread.")
            
        suggestion = email.meta_data['meeting_suggestion']
        
        # 2. Create the event
        event_title = suggestion.get('topic', 'Business Meeting')
        start_time = suggestion.get('start_time')
        end_time = suggestion.get('end_time')
        import re
        attendee_email = email.sender
        match = re.search(r'<(.*?)>', attendee_email)
        if match:
            attendee_email = match.group(1)
            
        attendee_list = [attendee_email]
        
        if provider == 'google':
            client = GoogleCalendarClient()
            if not client.connect():
                raise HTTPException(status_code=500, detail=f"Failed to connect to Google calendar.")
            result = client.create_event(
                summary=event_title,
                start_time=start_time,
                end_time=end_time,
                description=f"Automated booking via AI Assistant.\nSource Thread: {thread_id}",
                attendees=attendee_list
            )
        else:
            client = OutlookCalendarClient()
            if not client.connect():
                raise HTTPException(status_code=500, detail=f"Failed to connect to Outlook calendar.")
            result = client.create_event(
                subject=event_title,
                start_time=start_time,
                end_time=end_time,
                body_preview=f"Automated booking via AI Assistant.\nSource Thread: {thread_id}",
                attendees=attendee_list
            )
        
        # 3. Mark as booked in metadata
        from sqlalchemy.orm.attributes import flag_modified
        meta = dict(email.meta_data)
        meta['meeting_suggestion']['booked'] = True
        email.meta_data = meta
        flag_modified(email, "meta_data")
        db.commit()
        
        # 4. Clear calendar cache so it shows up in dashboard/agenda
        global calendar_cache
        calendar_cache.clear()
        
        return {"success": True, "data": result}
    except Exception as e:
        print(f"Error booking suggested meeting: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

@app.get("/api/tasks")
async def get_tasks(current_user: dict = Depends(get_current_user)):
    """Get all AI-extracted action items from emails"""
    db = SessionLocal()
    try:
        from database.models import Email
        # Find all emails with action_items in meta_data
        emails = db.query(Email).filter(
            Email.meta_data.isnot(None)
        ).all()
        
        tasks = []
        for e in emails:
            items = e.meta_data.get('action_items', [])
            for item in items:
                tasks.append({
                    "email_id": e.email_id,
                    "thread_id": e.thread_id,
                    "subject": e.subject,
                    "sender": e.sender,
                    "task": item,
                    "received_at": e.received_at.isoformat() if e.received_at else None
                })
        
        # Sort by latest first
        tasks.sort(key=lambda x: x['received_at'] or '', reverse=True)
        return {"success": True, "count": len(tasks), "data": tasks[:20]} # Limit to 20
    finally:
        db.close()

@app.get("/api/morning-brief")
async def get_morning_brief(current_user: dict = Depends(get_current_user)):
    """Aggregate a proactive summary for the executive"""
    db = SessionLocal()
    try:
        from database.models import Thread, Email, FollowupTask
        from agents.executive.scheduler import GoogleCalendarClient
        from datetime import datetime, timedelta, timezone
        
        today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0, tzinfo=None)
        
        # 1. Today's Meetings & Upcoming
        meetings_count = 0
        upcoming_count = 0
        try:
            cal = GoogleCalendarClient()
            if cal.connect():
                events = cal.get_upcoming_events(days=7) # Look ahead 7 days
                today_str = today_start.strftime('%Y-%m-%d')
                
                today_meetings = [e for e in events if e.get('start', {}).get('dateTime', '').startswith(today_str)]
                meetings_count = len(today_meetings)
                
                upcoming_meetings = [e for e in events if not e.get('start', {}).get('dateTime', '').startswith(today_str)]
                upcoming_count = len(upcoming_meetings)
        except: pass
        
        # 2. Urgent Emails (last 24h)
        yesterday = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=1)
        urgent_count = db.query(Thread).filter(
            Thread.status == 'urgent'
        ).count() # Total urgent
        
        # 3. Pending Follow-ups
        stale_count = db.query(FollowupTask).filter(FollowupTask.status == 'PENDING').count()
        
        # 4. Critical Action Items (last 48h for more context)
        task_count = 0
        search_date = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=2)
        emails_with_tasks = db.query(Email).filter(Email.meta_data.isnot(None), Email.received_at >= search_date).all()
        for e in emails_with_tasks:
            task_count += len(e.meta_data.get('action_items', []))

        # Build the brief string
        if meetings_count > 0:
            brief = f"Good morning, Abdullah. You have {meetings_count} meetings scheduled for today. "
        elif upcoming_count > 0:
            brief = f"Good morning, Abdullah. Your day is clear today, but you have {upcoming_count} meetings coming up this week. "
        else:
            brief = f"Good morning, Abdullah. You have no meetings on your calendar. "

        if urgent_count > 0:
            brief += f"There are {urgent_count} threads marked as urgent. "
        if task_count > 0:
            brief += f"I've identified {task_count} action items for you. "
        if stale_count > 0:
            brief += f"You have {stale_count} threads that may need a follow-up."

        return {
            "success": True,
            "brief": brief,
            "stats": {
                "meetings": meetings_count,
                "urgents": urgent_count,
                "tasks": task_count,
                "stale": stale_count
            }
        }
    finally:
        db.close()

@app.get("/api/contacts/{contact_id}/intelligence")
async def get_contact_intelligence(contact_id: int, current_user: dict = Depends(get_current_user)):
    """Deep historical overview for a specific contact"""
    db = SessionLocal()
    try:
        from database.models import Contact, Thread
        contact = db.query(Contact).get(contact_id)
        if not contact:
            raise HTTPException(status_code=404, detail="Contact not found")
            
        threads = db.query(Thread).filter(Thread.contact_id == contact_id).order_by(Thread.updated_at.desc()).limit(5).all()
        
        history = []
        for t in threads:
            history.append({
                "thread_id": t.thread_id,
                "subject": t.subject,
                "status": t.status,
                "last_update": t.updated_at.isoformat() if t.updated_at else None
            })
            
        return {
            "success": True,
            "contact": {
                "name": contact.contact_name,
                "domain": contact.email_domain,
                "interaction_count": len(contact.threads)
            },
            "recent_history": history
        }
    finally:
        db.close()

@app.get("/api/oauth/status")
async def get_api_oauth_status():
    """Wrapper for Outlook OAuth status to match frontend /api/ prefix"""
    return oauth_status()

@app.get("/api/gmail/oauth/status")
async def get_api_gmail_oauth_status():
    """Wrapper for Gmail OAuth status to match frontend /api/ prefix"""
    return await gmail_oauth_status()

# AI Assistant Chat Endpoint
@app.post("/api/assistant/extract-text")
async def extract_text(file: UploadFile = FastAPIFile(...), current_user: dict = Depends(get_current_user)):
    """Extract text from uploaded documents for AI context"""
    try:
        content = await file.read()
        text = ""
        
        if file.filename.lower().endswith('.pdf'):
            # Use PyMuPDF to extract text
            doc = fitz.open(stream=content, filetype="pdf")
            for page in doc:
                text += page.get_text()
            doc.close()
        elif file.filename.lower().endswith('.txt'):
            text = content.decode('utf-8', errors='ignore')
        else:
            return {"success": False, "error": "Unsupported file format. Please upload PDF or TXT."}
            
        return {
            "success": True, 
            "text": text[:10000],  # Cap at 10k chars for reasonable context
            "filename": file.filename
        }
    except Exception as e:
        print(f"Error extracting text: {e}")
        return {"success": False, "error": str(e)}

@app.get("/api/assistant/conversations")
async def get_conversations(current_user: dict = Depends(get_current_user)):
    """Get list of all conversations"""
    db = SessionLocal()
    try:
        from database.models import AssistantConversation
        conversations = db.query(AssistantConversation).order_by(AssistantConversation.last_message_at.desc()).all()
        return {
            "success": True,
            "data": [
                {
                    "id": c.id,
                    "title": c.title,
                    "created_at": c.created_at.isoformat(),
                    "last_message_at": c.last_message_at.isoformat()
                }
                for c in conversations
            ]
        }
    except Exception as e:
        print(f"Error fetching conversations: {e}")
        return {"success": False, "error": str(e)}
    finally:
        db.close()

@app.post("/api/assistant/conversations")
async def create_conversation(request: CreateConversationRequest, current_user: dict = Depends(get_current_user)):
    """Create a new conversation thread"""
    db = SessionLocal()
    try:
        from database.models import AssistantConversation
        new_conv = AssistantConversation(title=request.title)
        db.add(new_conv)
        db.commit()
        db.refresh(new_conv)
        return {
            "success": True,
            "data": {
                "id": new_conv.id,
                "title": new_conv.title
            }
        }
    except Exception as e:
        print(f"Error creating conversation: {e}")
        return {"success": False, "error": str(e)}
    finally:
        db.close()

@app.delete("/api/assistant/conversations/{conv_id}")
async def delete_conversation(conv_id: int, current_user: dict = Depends(get_current_user)):
    """Delete a conversation and its messages"""
    db = SessionLocal()
    try:
        from database.models import AssistantConversation, AssistantChat
        # Delete messages first
        db.query(AssistantChat).filter(AssistantChat.conversation_id == conv_id).delete()
        # Delete conversation
        db.query(AssistantConversation).filter(AssistantConversation.id == conv_id).delete()
        db.commit()
        return {"success": True}
    except Exception as e:
        print(f"Error deleting conversation: {e}")
        return {"success": False, "error": str(e)}
    finally:
        db.close()

@app.get("/api/assistant/history")
async def get_chat_history(conversation_id: Optional[int] = None, limit: int = 50, current_user: dict = Depends(get_current_user)):
    """Get recent chat history for a specific conversation"""
    db = SessionLocal()
    try:
        from database.models import AssistantChat
        query = db.query(AssistantChat)
        if conversation_id:
            query = query.filter(AssistantChat.conversation_id == conversation_id)
        
        # Fetch latest messages first, then reverse for display
        history = query.order_by(AssistantChat.timestamp.desc()).limit(limit).all()
        history.reverse() # Oldest to newest for UI
        
        return {
            "success": True,
            "data": [
                {
                    "id": h.id,
                    "role": h.role,
                    "content": h.content,
                    "timestamp": h.timestamp.isoformat()
                }
                for h in history
            ]
        }
    except Exception as e:
        print(f"Error fetching history: {e}")
        return {"success": False, "error": str(e)}
    finally:
        db.close()

@app.post("/api/assistant/chat")
async def assistant_chat(request: AssistantChatRequest, current_user: dict = Depends(get_current_user)):
    """General AI Assistant chat endpoint with conversation support"""
    print(f"Assistant chat request: {request.message[:50]}...")
    db = SessionLocal()
    try:
        from database.models import AssistantChat, AssistantConversation
        
        conv_id = request.conversation_id
        
        # Auto-create conversation if not provided
        if not conv_id:
            # Check if there's a recent active conversation or create new
            new_conv = AssistantConversation(title=request.message[:30] + "...")
            db.add(new_conv)
            db.commit()
            db.refresh(new_conv)
            conv_id = new_conv.id
        else:
            # Update last_message_at
            conv = db.query(AssistantConversation).filter(AssistantConversation.id == conv_id).first()
            if conv:
                conv.last_message_at = datetime.utcnow()
                # Update title if it's still default
                if conv.title == "New Conversation":
                    conv.title = request.message[:30] + "..."
                db.commit()

        # Process query via ExecutiveAssistant (handles RAG and message saving)
        assistant = ExecutiveAssistant(db)
        ai_response = assistant.answer_query(request.message, conversation_id=conv_id)
        
        return {
            "success": True,
            "response": ai_response,
            "conversation_id": conv_id
        }
    except Exception as e:
        print(f"Error in assistant chat: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

# Existing endpoints...
@app.get("/health")
def health_check():
    return {"status": "healthy"}

@app.get("/api/assistant/conversations")
async def get_assistant_conversations(current_user: dict = Depends(get_current_user)):
    db = SessionLocal()
    try:
        convs = db.query(AssistantConversation).order_by(desc(AssistantConversation.last_message_at)).all()
        return {
            "success": True,
            "data": [{"id": c.id, "title": c.title, "last_message_at": c.last_message_at} for c in convs]
        }
    finally:
        db.close()

@app.post("/api/assistant/conversations")
async def create_assistant_conversation(request: CreateConversationRequest, current_user: dict = Depends(get_current_user)):
    db = SessionLocal()
    try:
        new_conv = AssistantConversation(title=request.title)
        db.add(new_conv)
        db.commit()
        db.refresh(new_conv)
        return {"success": True, "data": {"id": new_conv.id, "title": new_conv.title}}
    finally:
        db.close()

@app.delete("/api/assistant/conversations/{conv_id}")
async def delete_assistant_conversation(conv_id: int, current_user: dict = Depends(get_current_user)):
    db = SessionLocal()
    try:
        conv = db.query(AssistantConversation).filter(AssistantConversation.id == conv_id).first()
        if not conv:
            raise HTTPException(status_code=404, detail="Conversation not found")
        # Delete related messages first
        db.query(AssistantChat).filter(AssistantChat.conversation_id == conv_id).delete()
        db.delete(conv)
        db.commit()
        return {"success": True}
    finally:
        db.close()

@app.get("/api/assistant/history")
async def get_assistant_history(conversation_id: Optional[int] = None, current_user: dict = Depends(get_current_user)):
    db = SessionLocal()
    try:
        query = db.query(AssistantChat)
        if conversation_id:
            query = query.filter(AssistantChat.conversation_id == conversation_id)
        
        history = query.order_by(AssistantChat.timestamp).all()
        return {
            "success": True,
            "data": [{"role": m.role, "content": m.content, "timestamp": m.timestamp} for m in history]
        }
    finally:
        db.close()

@app.get("/api/calendar/events")
async def get_calendar_events(days: int = 7, current_user: dict = Depends(get_current_user)):
    """Aggregate events from Google and Outlook Calendars"""
    from agents.executive.scheduler import GoogleCalendarClient, OutlookCalendarClient
    
    # Caching logic - DISABLED FOR REAL-TIME SYNC
    cache_key = f"calendar_events_{days}"
    # forcing fresh fetch every time for now to debug
    if cache_key in calendar_cache:
        del calendar_cache[cache_key]

    # Parallel fetch for performance if not in cache or expired
    import asyncio
    
    # Using asyncio.to_thread to prevent blocking the main event loop
    import asyncio
    
    def fetch_google_sync():
        events = []
        try:
            g_client = GoogleCalendarClient()
            if g_client.connect():
                g_events = g_client.get_upcoming_events(days=days)
                print(f"[API] Google returned {len(g_events)} events")
                for ev in g_events:
                    start = ev.get('start', {}).get('dateTime', ev.get('start', {}).get('date'))
                    end = ev.get('end', {}).get('dateTime', ev.get('end', {}).get('date'))
                    attendees = [{"name": att.get('displayName') or att.get('email'), "email": att.get('email'), "response": att.get('responseStatus')} for att in ev.get('attendees', [])]
                    events.append({
                        "id": ev.get('id'),
                        "title": ev.get('summary', 'No Title'),
                        "start": start,
                        "end": end,
                        "location": ev.get('location'),
                        "description": ev.get('description'),
                        "attendees": attendees,
                        "link": ev.get('hangoutLink') or ev.get('htmlLink'),
                        "source": "google",
                        "color": "#4285F4"
                    })
            else:
                print("[API] Google Calendar connection failed")
        except Exception as e: print(f"[API] Google fetch error: {e}")
        return events

    def fetch_outlook_sync():
        events = []
        try:
            o_client = OutlookCalendarClient()
            if o_client.connect():
                o_events = o_client.get_upcoming_events(days=days)
                print(f"[API] Outlook returned {len(o_events)} events")
                for ev in o_events:
                    start = ev.get('start', {}).get('dateTime')
                    end = ev.get('end', {}).get('dateTime')
                    attendees = [{"name": att.get('emailAddress', {}).get('name') or att.get('emailAddress', {}).get('address'), "email": att.get('emailAddress', {}).get('address'), "response": att.get('status', {}).get('response')} for att in ev.get('attendees', [])]
                    events.append({
                        "id": ev.get('id'),
                        "title": ev.get('subject', 'No Title'),
                        "start": start,
                        "end": end,
                        "location": ev.get('location', {}).get('displayName'),
                        "description": ev.get('bodyPreview'),
                        "attendees": attendees,
                        "link": ev.get('onlineMeetingUrl') or ev.get('webLink'),
                        "source": "outlook",
                        "color": "#0078D4"
                    })
            else:
                print("[API] Outlook Calendar connection failed")
        except Exception as e: print(f"[API] Outlook fetch error: {e}")
        return events

    g_results, o_results = await asyncio.gather(
        asyncio.to_thread(fetch_google_sync),
        asyncio.to_thread(fetch_outlook_sync)
    )
    all_events = g_results + o_results
    
    # DEBUG: Print titles to terminal
    print(f"[DEBUG] Total events found: {len(all_events)}")
    for ev in all_events:
        print(f"  - [{ev['source'].upper()}] {ev['title']} at {ev['start']}")

    # Save to cache
    now_ts = time.time()
    calendar_cache[cache_key] = (now_ts, all_events)

    return {
        "success": True,
        "data": all_events
    }

@app.post("/api/calendar/events")
async def create_calendar_event(request: CreateEventRequest, current_user: dict = Depends(get_current_user)):
    """Create a new event on the selected calendar provider"""
    from agents.executive.scheduler import GoogleCalendarClient, OutlookCalendarClient
    global calendar_cache
    
    try:
        # --- Clean up description BEFORE creating the event ---
        description = request.description or ""
        if "Need to reschedule?" in description:
            import re
            description = re.sub(r'Need to reschedule\?.*$', '', description, flags=re.IGNORECASE | re.DOTALL).strip()
            # Also remove any leftover HTML tags if they were missed
            description = re.sub(r'<[^>]+>', '', description).strip()

        print(f"[DEBUG] Creating event: {request.provider.upper()} - {request.title} from {request.start_time} to {request.end_time}")
        if request.provider == 'google':
            client = GoogleCalendarClient()
            if client.connect():
                result = client.create_event(
                    summary=request.title,
                    start_time=request.start_time,
                    end_time=request.end_time,
                    description=description,
                    attendees=request.attendees
                )
                print(f"[DEBUG] Google Creation Result: {json.dumps(result, indent=2)}")
                # Fetch the hangout link from the full result
                meet_link = result.get('hangoutLink') or result.get('htmlLink') or ""
                
                # --- Send Professional Inbox Notification ---
                try:
                    from agents.rfq_agent.gmail_api_client import GmailAPIFetcher
                    gmail = GmailAPIFetcher()
                    if gmail.connect():
                        for email_addr in request.attendees:
                            email_body = f"""Hi,

I've scheduled a meeting with you regarding: {request.title}

Time: {request.start_time} (UTC)

{f"Agenda: {description}" if description else ""}

You can join the meeting directly via Google Meet here:
{meet_link}

Looking forward to our discussion.

Best regards,
AI Executive Assistant
"""
                            gmail.send_immediate_email(
                                to=email_addr,
                                subject=f"Meeting Scheduled: {request.title}",
                                body=email_body
                            )
                        print(f"[API] Professional notifications sent to {len(request.attendees)} guests with link: {meet_link}")
                except Exception as ex:
                    print(f"[API] Manual notification failed: {ex}")
                # ---------------------------------------------

                global calendar_cache
                calendar_cache.clear()
                # result already assigned at line 2782
        elif request.provider == 'outlook':
            client = OutlookCalendarClient()
            if client.connect():
                result = client.create_event(
                    subject=request.title,
                    start_time=request.start_time,
                    end_time=request.end_time,
                    body_preview=request.description,
                    attendees=request.attendees
                )
                calendar_cache.clear()
        
        
        if request.thread_id:
            db = SessionLocal()
            try:
                from database.models import Email
                from sqlalchemy.orm.attributes import flag_modified
                emails = db.query(Email).filter(Email.thread_id == request.thread_id).all()
                for email in emails:
                    if email.meta_data and 'meeting_suggestion' in email.meta_data:
                        meta = dict(email.meta_data)
                        meta['meeting_suggestion']['booked'] = True
                        email.meta_data = meta
                        flag_modified(email, "meta_data")
                
                # Force cache update for status
                from database.models import Thread
                thread = db.query(Thread).filter(Thread.thread_id == request.thread_id).first()
                if thread:
                    thread.status = 'MEETING_BOOKED'
                
                db.commit()
                # HARD CLEAR CALENDAR CACHE
                calendar_cache = {} 
            finally:
                db.close()

        # Final return after provider logic
        if 'result' in locals():
            return result
            
        return {"success": False, "error": f"Provider '{request.provider}' not connected or unsupported"}
    except Exception as e:
        print(f"Error creating calendar event: {e}")
        return {"success": False, "error": str(e)}

@app.delete("/api/calendar/events/{provider}/{event_id:path}")
async def delete_calendar_event(provider: str, event_id: str, current_user: dict = Depends(get_current_user)):
    """Delete an event from the calendar provider"""
    from agents.executive.scheduler import GoogleCalendarClient, OutlookCalendarClient
    
    try:
        if provider == 'google':
            client = GoogleCalendarClient()
            if client.connect():
                result = client.delete_event(event_id)
                global calendar_cache
                calendar_cache.clear()
                return result
        elif provider == 'outlook':
            client = OutlookCalendarClient()
            if client.connect():
                result = client.delete_event(event_id)
                calendar_cache.clear()
                return result
        
        return {"success": False, "error": f"Provider '{provider}' not connected or unsupported"}
    except Exception as e:
        print(f"Error deleting calendar event: {e}")
        return {"success": False, "error": str(e)}

# ==========================================
# FOLLOW-UP ASSISTANT ENDPOINTS
# ==========================================

@app.get("/api/followups")
async def get_followups(current_user: str = Depends(get_current_user)):
    """Get pending follow-up suggestions"""
    from database.models import FollowupTask, Thread
    db = SessionLocal()
    try:
        followups = db.query(FollowupTask).filter(FollowupTask.status == 'PENDING').all()
        results = []
        for f in followups:
            thread = db.query(Thread).filter(Thread.thread_id == f.thread_id).first()
            results.append({
                "id": f.id,
                "thread_id": f.thread_id,
                "subject": thread.subject if thread else "Unknown Subject",
                "recipient": f.recipient,
                "suggested_body": f.suggested_body,
                "due_at": f.due_at.isoformat() if f.due_at else None,
                "created_at": f.created_at.isoformat()
            })
        return results
    finally:
        db.close()

@app.post("/api/followups/{task_id}/dismiss")
async def dismiss_followup(task_id: int, current_user: str = Depends(get_current_user)):
    """Dismiss a follow-up suggestion"""
    from database.models import FollowupTask
    db = SessionLocal()
    try:
        task = db.query(FollowupTask).filter(FollowupTask.id == task_id).first()
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
        task.status = 'DISMISSED'
        db.commit()
        return {"status": "success"}
    finally:
        db.close()

@app.post("/api/followups/{task_id}/approve")
async def approve_followup(task_id: int, current_user: str = Depends(get_current_user)):
    """Convert a follow-up suggestion into a real draft"""
    from database.models import FollowupTask, Thread, DraftReply
    from agents.rfq_agent.email_fetcher import EmailFetcher
    
    db = SessionLocal()
    try:
        task = db.query(FollowupTask).filter(FollowupTask.id == task_id).first()
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
        
        provider = "gmail" if "@gmail.com" in (task.recipient or "").lower() else "outlook"
        fetcher = EmailFetcher(provider=provider)
        if not fetcher.connect():
            raise HTTPException(status_code=500, detail=f"Could not connect to {provider}")
        
        try:
            thread = db.query(Thread).filter(Thread.thread_id == task.thread_id).first()
            subject = f"Follow-up: {thread.subject}" if thread else "Follow-up"
            
            draft_result = fetcher.fetcher.create_draft(
                to=task.recipient,
                subject=subject,
                body=task.suggested_body
            )
            
            if draft_result.get('success'):
                new_draft = DraftReply(
                    thread_id=task.thread_id,
                    recipient=task.recipient,
                    subject=subject,
                    body=task.suggested_body,
                    email_provider=provider,
                    provider_draft_id=draft_result['draft_id'],
                    status='DRAFT'
                )
                db.add(new_draft)
                task.status = 'COMPLETED'
                db.commit()
                return {"status": "success", "draft_id": draft_result['draft_id']}
            else:
                raise Exception(draft_result.get('error', 'Unknown Error'))
        finally:
            fetcher.disconnect()
    except Exception as e:
        print(f"Error approving followup: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()
# Mounts at the end to avoid intercepting API routes
app.mount("/storage", StaticFiles(directory="storage"), name="storage")
app.mount("/", StaticFiles(directory="ui", html=True), name="ui")
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8069)