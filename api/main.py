from dotenv import load_dotenv
# Load .env FIRST before any other imports
load_dotenv()

import os
# Allow OAuth scope changes (Google sometimes adds openid/email automatically)
os.environ['OAUTHLIB_RELAX_TOKEN_SCOPE'] = '1'

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, RedirectResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Dict, Optional, List
from sqlalchemy import desc, func, or_, text
from database.models import Client, Project, Tender, Email, Document, DraftEmail, RFIDraft, FileLink, AgentHandover, AuditLog
from database.connection import SessionLocal
import msal
import json
from pathlib import Path
import secrets
import webbrowser
from datetime import datetime

# Pydantic models for Assistant
class CreateConversationRequest(BaseModel):
    title: Optional[str] = "New Conversation"

class AssistantChatRequest(BaseModel):
    message: str
    context: Optional[str] = None
    conversation_id: Optional[int] = None

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
You are the AI Assistant for the RFQ Agent platform.
Your goal is to help users manage their tenders, RFQs, and business documents.
You can provide general assistance, summarize documents, and answer business queries.

IMPORTANT: 
- If asked "Who are you?" or about your identity, respond that you are the "RFQ Agent AI Assistant". 
- NEVER mention "Pixtral", "Mistral", or any specific LLM model name. 
- Maintain a professional, helpful, and business-focused tone.
"""

app = FastAPI(title="RFQ Agent API")

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

@app.get("/api/oauth/login")
def oauth_login():
    """Initiate OAuth2 login flow"""
    
    # Generate state for CSRF protection
    state = secrets.token_urlsafe(32)
    oauth_sessions[state] = {'started': True}
    
    # Build MSAL app
    msal_app = get_msal_app()
    
    # Get authorization URL
    auth_url = msal_app.get_authorization_request_url(
        SCOPES,
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
            include_granted_scopes='true',
            prompt='consent'
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
from database.models import DraftEmail, Email, Tender, Document
from agents.rfq_agent.outlook_graph import OutlookGraphFetcher
from agents.rfq_agent.gmail_api_client import GmailAPIFetcher
from sqlalchemy import desc, text

class DraftUpdate(BaseModel):
    subject: Optional[str] = None
    body: Optional[str] = None

class DraftEnhance(BaseModel):
    instructions: str

class DraftCreate(BaseModel):
    tender_id: Optional[str] = None
    recipient: str
    subject: str
    body: str
    draft_type: str = "RESPONSE"
    in_reply_to_email_id: Optional[str] = None



@app.get("/api/drafts")
async def get_drafts(tender_id: Optional[str] = None):
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
                    "tender_id": d.tender_id,
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
async def get_draft(draft_id: int):
    """Get a specific draft by ID"""
    db = SessionLocal()
    
    try:
        draft = db.query(DraftEmail).filter(DraftEmail.id == draft_id).first()
        
        if not draft:
            raise HTTPException(status_code=404, detail="Draft not found")
        
        return {
            "success": True,
            "draft": {
                "id": draft.id,
                "tender_id": draft.tender_id,
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
async def create_draft(draft_data: DraftCreate):
    """Create a new draft email"""
    db = SessionLocal()
    
    try:
        # Detect provider from tender source
        provider = 'outlook'  # Default
        if draft_data.tender_id:
            tender = db.query(Tender).filter(Tender.tender_id == draft_data.tender_id).first()
            if tender and tender.source:
                if 'gmail' in tender.source.lower():
                    provider = 'gmail'
        
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
            tender_id=draft_data.tender_id,
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
async def update_draft(draft_id: int, draft_update: DraftUpdate):
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
async def send_draft(draft_id: int):
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
async def enhance_draft(draft_id: int, enhancement: DraftEnhance):
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
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

@app.delete("/api/drafts/{draft_id}")
async def delete_draft(draft_id: int):
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
async def get_session_summary(from_time: str, to_time: str):
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

        # Fetch emails processed in this window that are tenders
        emails = db.query(Email).filter(
            Email.is_tender == True,
            Email.processed == True,
            Email.created_at >= start,
            Email.created_at <= end
        ).order_by(Email.created_at.desc()).limit(100).all()

        # For each email, get docs count and tender subject
        results = []
        for e in emails:
            doc_count = db.query(func.count(Document.id)).filter(
                Document.tender_id == e.tender_id
            ).scalar() if e.tender_id else 0

            results.append({
                "email_id": e.id,
                "subject": e.subject,
                "sender": e.sender,
                "tender_id": e.tender_id,
                "received_at": e.received_at.isoformat() if e.received_at else None,
                "processed_at": e.created_at.isoformat() if e.created_at else None,
                "doc_count": doc_count,
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
async def get_emails(tender_id: Optional[str] = None, status: Optional[str] = None, include_all: bool = True):
    """Get all emails, optionally filtered"""
    db = SessionLocal()
    
    try:
        query = db.query(Email)
        
        if tender_id:
            query = query.filter(Email.tender_id == tender_id)
        
        # Default behavior: Show everything unless a specific status is requested
        # (include_all is True by default now)
        if status:
            if status == "processed":
                query = query.filter(Email.processed == True)
            elif status == "unprocessed":
                query = query.filter(Email.processed == False)
            elif status == "tender":
                query = query.filter(Email.is_tender == True)
            elif status == "junk":
                query = query.filter(Email.is_tender == False)
        
        emails = query.order_by(desc(Email.id)).all()
        
        # Get active drafts to map them back to emails (like Gmail)
        drafts = db.query(DraftEmail).filter(DraftEmail.status == 'DRAFT').all()
        draft_map = {d.in_reply_to_email_id: d.id for d in drafts if d.in_reply_to_email_id}
        
        # Get document counts per tender_id
        doc_counts = {}
        tender_ids = [e.tender_id for e in emails if e.tender_id]
        if tender_ids:
            # Count documents for each unique tender_id
            counts = db.query(Document.tender_id, func.count(Document.id)).filter(
                Document.tender_id.in_(tender_ids)
            ).group_by(Document.tender_id).all()
            doc_counts = {tid: count for tid, count in counts}

        return {
            "success": True,
            "count": len(emails),
            "data": [
                {
                    "id": e.id,
                    "email_id": e.email_id,
                    "tender_id": e.tender_id,
                    "subject": e.subject,
                    "sender": e.sender,
                    "from": e.sender,  # Alias for frontend
                    "date": e.received_at.isoformat() if e.received_at else None, # Alias for frontend
                    "body": e.body[:200] if e.body else None,  # Preview only
                    "received_at": e.received_at.isoformat() if e.received_at else None,
                    "is_tender": e.is_tender,
                    "processed": e.processed,
                    "attachments": doc_counts.get(e.tender_id, 0) if e.is_tender else 0,
                    "status": "tender" if e.is_tender else "processed" if e.processed else "unprocessed",
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
async def get_email(email_id: int):
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
                "tender_id": email.tender_id,
                "subject": email.subject,
                "sender": email.sender,
                "body": email.body,
                "received_at": email.received_at.isoformat() if email.received_at else None,
                "is_tender": email.is_tender,
                "processed": email.processed
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

@app.post("/api/emails/{email_id}/archive")
async def archive_email(email_id: int):
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

@app.get("/api/documents/{doc_id}")
async def get_document(doc_id: int):
    """Get metadata for a specific document"""
    db = SessionLocal()
    try:
        doc = db.query(Document).filter(Document.id == doc_id).first()
        if not doc:
            raise HTTPException(status_code=404, detail="Document not found")
        # Calculate view URL relative to /storage mount
        # If path is ./storage/tenders/file.pdf, relative is tenders/file.pdf
        rel_path = doc.file_path
        if rel_path.startswith('./'):
            rel_path = rel_path[2:]
        if rel_path.startswith('storage/'):
            rel_path = rel_path[len('storage/'):]
        
        # Replace backslashes with forward slashes for URL
        rel_path = rel_path.replace('\\', '/')
        
        return {
            "success": True,
            "data": {
                "id": doc.id,
                "filename": doc.filename,
                "file_path": doc.file_path,
                "view_url": f"/storage/{rel_path}",
                "category": doc.category,
                "tender_id": doc.tender_id,
                "version": doc.version,
                "uploaded_at": doc.uploaded_at.isoformat() if doc.uploaded_at else None
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

@app.delete("/api/documents/{doc_id}")
async def delete_document(doc_id: int):
    """Delete a document from DB and storage"""
    db = SessionLocal()
    try:
        doc = db.query(Document).filter(Document.id == doc_id).first()
        if not doc:
            raise HTTPException(status_code=404, detail="Document not found")
            
        # Optional: Delete physical file
        try:
            file_path = Path(doc.file_path)
            if file_path.exists():
                file_path.unlink()
        except Exception as fe:
            print(f"Warning: Could not delete physical file: {fe}")
            
        db.delete(doc)
        db.commit()
        return {"success": True, "message": "Document deleted successfully"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

@app.post("/api/documents/upload")
async def upload_document(file: UploadFile = FastAPIFile(...)):
    """Upload a new document to storage and database"""
    db = SessionLocal()
    try:
        # Create storage directories if they don't exist
        upload_dir = Path("storage/manual_uploads")
        upload_dir.mkdir(parents=True, exist_ok=True)
        
        # Read file content
        content = await file.read()
        file_hash = hashlib.sha256(content).hexdigest()
        
        # Define file path
        filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{file.filename}"
        file_path = upload_dir / filename
        
        # Save file to disk
        with open(file_path, "wb") as f:
            f.write(content)
            
        # Create database entry
        new_doc = Document(
            filename=file.filename,
            original_filename=file.filename,
            file_path=str(file_path),
            file_hash=file_hash,
            file_size_bytes=len(content),
            mime_type=file.content_type,
            category='Irrelevant',  # Explicitly mark manual uploads as Irrelevant initially
            uploaded_at=datetime.utcnow(),
            tender_id='N/A',    # Default tender ID
            is_correct=False,   # Manual uploads are unverified by default
            rejection_reason='Manually uploaded file'
        )
        
        db.add(new_doc)
        db.commit()
        db.refresh(new_doc)
        
        return {"success": True, "document_id": new_doc.id}
    except Exception as e:
        db.rollback()
        print(f"Upload error: {e}")
        return {"success": False, "error": str(e)}
    finally:
        db.close()

@app.get("/api/dashboard/stats")
async def get_dashboard_stats():
    """Get aggregate statistics for the dashboard"""
    db = SessionLocal()
    try:
        # Count various entities with existence checks
        active_tenders = db.query(Project).count()
        total_emails = db.query(Email).count()
        unprocessed_emails = db.query(Email).filter(Email.processed == False).count()
        # count ONLY RFI/Draft status
        pending_rfis = db.query(DraftEmail).filter(DraftEmail.status == 'DRAFT').count()
        total_clients = db.query(Client).count()
        
        return {
            "success": True,
            "data": {
                "activeTenders": active_tenders,
                "unreadEmails": total_emails,
                "unprocessedEmails": unprocessed_emails,
                "pendingRFIs": pending_rfis,
                "totalClients": total_clients
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
                "totalClients": 0
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
async def get_system_status():
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
async def toggle_document_correct(doc_id: int):
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
async def upload_draft_attachment(draft_id: int, file: UploadFile = FastAPIFile(...)):
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

@app.post("/api/process-emails")
async def process_emails_endpoint(background_tasks: BackgroundTasks):
    """Trigger the email processing workflow in the background (or sync in DEMO)"""
    try:
        from scripts.run_rfq_agent import DEMO_MODE
        
        # Run the actual processing logic in background for real use
        background_tasks.add_task(process_email_batch)
        
        return {
            "success": True,
            "message": "Email processing started in background.",
        }
    except Exception as e:
        print(f"Error starting background email processing: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/agent/status")
async def get_agent_status():
    """Get the latest progress from the AuditLog table"""
    db = SessionLocal()
    try:
        from sqlalchemy import desc
        logs = db.query(AuditLog).filter(AuditLog.action.like("PROGRESS:%")).order_by(desc(AuditLog.timestamp)).limit(20).all()
        
        # Determine if active by looking at the last few minutes
        is_active = False
        debug_info = {}
        if logs:
            last_timestamp = logs[0].timestamp
            now = datetime.utcnow()
            time_diff = (now - last_timestamp).total_seconds()
            
            # Cases for is_active:
            # 1. If last log is very recent (less than 2 mins)
            if time_diff < 120:
                is_active = True
            # 2. If it's a "ongoing" log (not complete) and within the last 30 mins
            elif time_diff < 1800 and not any(kw in logs[0].action.lower() for kw in ["complete", "finished", "failed"]):
                is_active = True
        
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

@app.get("/api/clients/{client_id}")
async def get_client_api(client_id: int):
    """Get a specific client by ID"""
    db = SessionLocal()
    try:
        client = db.query(Client).filter(Client.id == client_id).first()
        if not client:
            raise HTTPException(status_code=404, detail="Client not found")
        return {
            "success": True,
            "data": {
                "id": client.id,
                "name": client.client_name,
                "email": client.email_domain,
                "first_seen": client.first_seen.isoformat() if client.first_seen else None,
                "last_contact": client.last_contact.isoformat() if client.last_contact else None,
                "tenders": len(client.tenders) if client.tenders else 0
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()
@app.get("/api/clients")
async def get_clients_api():
    """Get all clients"""
    db = SessionLocal()
    try:
        clients = db.query(Client).all()
        return {
            "success": True,
            "count": len(clients),
            "data": [
                {
                    "id": c.id,
                    "name": c.client_name, # Alias for frontend
                    "email": c.email_domain, # Alias for frontend
                    "phone": "N/A", # Placeholder
                    "tenders": len(c.tenders) if c.tenders else 0,
                    "status": "active" # Placeholder
                }
                for c in clients
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

@app.get("/api/tenders")
async def get_tenders(status: Optional[str] = None):
    """Get all tenders with optional status filter"""
    db = SessionLocal()
    try:
        query = db.query(Tender)
        if status:
            query = query.filter(Tender.status == status)
        tenders = query.order_by(desc(Tender.updated_at)).all()
        
        # Get document counts for each tender
        doc_counts = {}
        for t in tenders:
            count = db.query(Document).filter(Document.tender_id == t.tender_id).count()
            doc_counts[t.tender_id] = count

        return {
            "success": True,
            "data": [
                {
                    "id": t.id,
                    "tender_id": t.tender_id,
                    "status": t.status.lower() if t.status else "pending",
                    "client": t.client_name, # Alias for frontend
                    "subject": t.project_name, # Alias for frontend
                    "date": t.created_at.isoformat() if t.created_at else None, # Alias for frontend
                    "client_name": t.client_name,
                    "project_name": t.project_name,
                    "created_at": t.created_at.isoformat() if t.created_at else None,
                    "updated_at": t.updated_at.isoformat() if t.updated_at else None,
                    "documents": doc_counts.get(t.tender_id, 0)
                }
                for t in tenders
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

@app.get("/api/tenders/{tender_id}")
async def get_single_tender(tender_id: str):
    """Get details for a specific tender"""
    db = SessionLocal()
    try:
        from database.models import Tender
        tender = db.query(Tender).filter(Tender.tender_id == tender_id).first()
        if not tender:
            raise HTTPException(status_code=404, detail="Tender not found")
        return {
            "id": tender.id,
            "tender_id": tender.tender_id,
            "status": tender.status,
            "client_name": tender.client_name,
            "project_name": tender.project_name,
            "tender_reference": tender.tender_reference,
            "created_at": tender.created_at.isoformat() if tender.created_at else None
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

@app.get("/api/tenders/{tender_id}/documents")
async def get_tender_documents(tender_id: str):
    """Get documents associated with a tender (or all if undefined)"""
    db = SessionLocal()
    try:
        # If 'undefined', 'all', or empty, return all documents for the general view
        if not tender_id or tender_id in ('undefined', 'all'):
            print("DEBUG: Fetching ALL documents")
            docs = db.query(Document).order_by(desc(Document.uploaded_at)).all()
        else:
            print(f"DEBUG: Fetching documents for tender: {tender_id}")
            docs = db.query(Document).filter(Document.tender_id == tender_id).all()
        
        print(f"DEBUG: Found {len(docs)} documents in DB")
            
        # Get tender grouping context (Email info)
        email_info = {}
        tender_ids = list(set([d.tender_id for d in docs if d.tender_id]))
        if tender_ids:
            emails = db.query(Email).filter(Email.tender_id.in_(tender_ids)).all()
            for e in emails:
                if e.tender_id not in email_info:
                    email_info[e.tender_id] = {
                        "subject": e.subject,
                        "sender": e.sender
                    }

        results = []
        for d in docs:
            # Fetch tender for updated_at
            t = db.query(Tender).filter(Tender.tender_id == d.tender_id).first()
            results.append({
                "id": d.id,
                "name": d.filename,                               # Frontend expects .name
                "type": (d.category or 'Irrelevant').lower(),     # Handle None category
                "tender": d.tender_id or 'N/A',                   # Handle None tender_id
                "tender_updated_at": t.updated_at.isoformat() if t and t.updated_at else d.uploaded_at.isoformat(),
                "source_email": email_info.get(d.tender_id, {}).get('subject', 'N/A'),
                "source_sender": email_info.get(d.tender_id, {}).get('sender', 'N/A'),
                "version": d.version or 1,
                "size": f"{d.file_size_bytes / 1024:.1f} KB" if d.file_size_bytes else "0 KB",
                "date": d.uploaded_at.isoformat() if d.uploaded_at else datetime.utcnow().isoformat(),
                "is_correct": d.is_correct if d.is_correct is not None else True
            })

        # Inject empty tenders if fetching all
        if not tender_id or tender_id in ('undefined', 'all'):
            # Get all tenders from the Tender table
            all_tenders = db.query(Tender).all()
            existing_tenders = {d.tender_id for d in docs if d.tender_id}
            
            for t in all_tenders:
                if t.tender_id and t.tender_id not in existing_tenders:
                    existing_tenders.add(t.tender_id)
                    results.append({
                        "id": f"empty_{t.id}",
                        "name": "No documents attached",
                        "type": "missing",
                        "tender": t.tender_id,
                        "tender_updated_at": t.updated_at.isoformat() if t.updated_at else t.created_at.isoformat(),
                        "source_email": t.project_name or t.tender_reference or t.tender_id,
                        "source_sender": t.client_name or "Unknown",
                        "version": "-",
                        "size": "0 KB",
                        "date": t.created_at.isoformat() if t.created_at else datetime.utcnow().isoformat(),
                        "is_correct": False
                    })

        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
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
async def extract_text(file: UploadFile = FastAPIFile(...)):
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
async def get_conversations():
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
async def create_conversation(request: CreateConversationRequest):
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
async def delete_conversation(conv_id: int):
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
async def get_chat_history(conversation_id: Optional[int] = None, limit: int = 50):
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
async def assistant_chat(request: AssistantChatRequest):
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

        # Save user message to database
        user_msg = AssistantChat(role='user', content=request.message, conversation_id=conv_id)
        db.add(user_msg)
        db.commit()

        ai_client = PixtralClient()
        
        user_prompt = request.message
        if request.context:
            user_prompt = f"Context from documents:\n{request.context}\n\nUser Question: {request.message}"
            
        result = ai_client.chat(
            system_prompt=ASSISTANT_SYSTEM_PROMPT,
            user_prompt=user_prompt,
            temperature=0.7
        )
        
        if not result or result.get('error'):
            raise HTTPException(status_code=500, detail=result.get('error', "AI chat failed"))
            
        ai_response = result.get('response', "I'm sorry, I couldn't generate a response.")
        
        # Save assistant message to database
        assistant_msg = AssistantChat(role='assistant', content=ai_response, conversation_id=conv_id)
        db.add(assistant_msg)
        db.commit()
        
        return {
            "success": True,
            "response": ai_response,
            "conversation_id": conv_id,
            "reasoning": result.get('reasoning')
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

# Mounts at the end to avoid intercepting API routes
app.mount("/storage", StaticFiles(directory="storage"), name="storage")
app.mount("/", StaticFiles(directory="ui", html=True), name="ui")
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5001)