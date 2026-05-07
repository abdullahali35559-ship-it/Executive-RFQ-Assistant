from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session
from sqlalchemy import desc
from database.models import Attachment, User, Thread, Email
from config.database import get_db
from auth.dependencies import get_current_user
from datetime import datetime
import os

router = APIRouter(tags=["attachments"])

@router.get("/api/attachments")
async def get_all_attachments(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    # Join with Thread and Email to get full context
    results = db.query(
        Attachment,
        Thread.contact_name,
        Thread.source_email,
        Email.subject.label("email_subject"),
        Email.received_at.label("email_received_at"),
        Email.body.label("email_body")
    ).outerjoin(
        Thread, Attachment.thread_id == Thread.thread_id
    ).outerjoin(
        Email, Attachment.email_id == Email.email_id
    ).order_by(desc(Attachment.uploaded_at)).all()
    
    # Format results
    data = []
    for att, contact_name, source_email, email_subject, email_received_at, email_body in results:
        doc = {
            "id": att.id,
            "thread_id": att.thread_id,
            "email_id": att.email_id,
            "category": att.category,
            "filename": att.filename,
            "original_filename": att.original_filename,
            "file_path": att.file_path,
            "file_size_bytes": att.file_size_bytes,
            "doc_type": att.doc_type,
            "summary": att.summary,
            "is_correct": att.is_correct,
            "version": att.version,
            "uploaded_at": att.uploaded_at,
            "source": att.source,
            "sender_name": contact_name or "Unknown",
            "sender_email": source_email or "N/A",
            "email_subject": email_subject or "Direct Upload",
            "email_received_at": email_received_at,
            "email_body": email_body or "No body content available"
        }
        data.append(doc)
        
    return {"success": True, "data": data}

@router.get("/api/attachments/{att_id}")
async def get_attachment(att_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    att = db.query(Attachment).filter(Attachment.id == att_id).first()
    if not att:
        raise HTTPException(status_code=404, detail="Attachment not found")
    
    # In a real app, this would return the file content or a signed URL
    # For now, return metadata
    return {
        "success": True,
        "data": {
            "id": att.id,
            "filename": att.filename,
            "original_filename": att.original_filename,
            "size": att.file_size_bytes,
            "summary": att.summary,
            "type": att.doc_type,
            "view_url": f"/api/attachments/{att_id}/download"
        }
    }

@router.get("/api/attachments/{att_id}/download")
async def download_attachment(att_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    att = db.query(Attachment).filter(Attachment.id == att_id).first()
    if not att or not att.file_path or not os.path.exists(att.file_path):
        raise HTTPException(status_code=404, detail="File not found")
    
    from fastapi.responses import FileResponse
    import mimetypes
    
    # Force mimetypes for common construction docs
    file_ext = os.path.splitext(att.file_path)[1].lower()
    if file_ext == '.pdf':
        mime_type = "application/pdf"
    elif file_ext in ['.jpg', '.jpeg', '.png', '.gif']:
        mime_type = f"image/{file_ext[1:]}"
    elif file_ext == '.txt':
        mime_type = "text/plain"
    else:
        mime_type, _ = mimetypes.guess_type(att.file_path)
    
    if not mime_type:
        mime_type = "application/octet-stream"

    # Use inline disposition so it opens in browser (e.g. Chrome's PDF viewer)
    # Removing 'filename' parameter from FileResponse often helps browser decide to inline
    return FileResponse(
        att.file_path, 
        content_disposition_type='inline',
        media_type=mime_type
    )
