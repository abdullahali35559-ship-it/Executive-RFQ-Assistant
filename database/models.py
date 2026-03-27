from sqlalchemy import Column, Integer, String, Boolean, DateTime, Float, ARRAY, Text, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from datetime import datetime
from config.database import Base

class Client(Base):
    __tablename__ = 'clients'
    
    id = Column(Integer, primary_key=True)
    client_name = Column(String(255), nullable=False)
    email_domain = Column(String(100))
    contact_emails = Column(ARRAY(Text))
    first_seen = Column(DateTime, default=datetime.utcnow)
    last_contact = Column(DateTime)
    total_projects = Column(Integer, default=0)
    meta_data = Column(JSONB)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    projects = relationship('Project', back_populates='client')
    tenders = relationship('Tender', back_populates='client')

class Project(Base):
    __tablename__ = 'projects'
    
    id = Column(Integer, primary_key=True)
    client_id = Column(Integer, ForeignKey('clients.id'), nullable=False)
    project_name = Column(String(255))
    project_reference = Column(String(100))
    tender_id = Column(String(50), unique=True)
    status = Column(String(50), default='ACTIVE')
    folder_path = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    meta_data = Column(JSONB)
    
    # Relationships
    client = relationship('Client', back_populates='projects')
    tenders = relationship('Tender', back_populates='project')

class Tender(Base):
    __tablename__ = 'tenders'
    
    id = Column(Integer, primary_key=True)
    tender_id = Column(String(50), unique=True, nullable=False)
    status = Column(String(50), nullable=False, default='PROCESSING')
    
    # Foreign Keys
    client_id = Column(Integer, ForeignKey('clients.id'))
    project_id = Column(Integer, ForeignKey('projects.id'))
    
    # Legacy fields (kept for backward compatibility)
    client_name = Column(String(255))
    project_name = Column(String(255))
    tender_reference = Column(String(100))
    submission_deadline = Column(DateTime(timezone=True))
    rfi_deadline = Column(DateTime(timezone=True))
    location = Column(String(255), default='Saudi Arabia')
    trade = Column(String(100))
    current_agent = Column(String(50), default='RFQ_AGENT')
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    source = Column(String(50))
    source_email = Column(String(255))
    source_sender = Column(String(255))
    
    # Relationships
    client = relationship('Client', back_populates='tenders')
    project = relationship('Project', back_populates='tenders')

class Email(Base):
    __tablename__ = 'emails'
    
    id = Column(Integer, primary_key=True)
    tender_id = Column(String(50))
    email_id = Column(String(255), unique=True)
    subject = Column(Text)
    sender = Column(String(255))
    recipients = Column(ARRAY(Text))
    body = Column(Text)
    received_at = Column(DateTime(timezone=True))
    is_tender = Column(Boolean)
    detection_confidence = Column(Float)
    keywords_found = Column(ARRAY(Text))
    processed = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

class Document(Base):
    __tablename__ = 'documents'
    
    id = Column(Integer, primary_key=True)
    tender_id = Column(String(50))
    filename = Column(String(255), nullable=False)
    original_filename = Column(String(255))
    file_path = Column(Text, nullable=False)
    file_hash = Column(String(64), nullable=False)
    file_size_bytes = Column(Integer)
    category = Column(String(50))
    classification_confidence = Column(Float)
    mime_type = Column(String(100))
    is_read_only = Column(Boolean, default=True)
    is_correct = Column(Boolean, default=True)
    rejection_reason = Column(Text)
    version = Column(Integer, default=1)
    is_addendum = Column(Boolean, default=False)
    
    # Version tracking
    previous_version_id = Column(Integer, ForeignKey('documents.id'))
    version_reason = Column(Text)
    replaced_at = Column(DateTime)
    uploaded_at = Column(DateTime, default=datetime.utcnow)
    classified_by = Column(String(50), default='RFQ_AGENT')
    source = Column(String(50))

class RFIDraft(Base):
    __tablename__ = 'rfi_drafts'
    
    id = Column(Integer, primary_key=True)
    tender_id = Column(String(50))
    rfi_id = Column(String(50))
    category = Column(String(50))
    missing_item = Column(String(255))
    draft_subject = Column(Text)
    draft_body = Column(Text)
    priority = Column(String(20))
    status = Column(String(50), default='DRAFT')
    created_by = Column(String(50), default='RFQ_AGENT')
    created_at = Column(DateTime, default=datetime.utcnow)
    sent_at = Column(DateTime)

class DraftEmail(Base):
    __tablename__ = 'draft_emails'
    
    id = Column(Integer, primary_key=True)
    tender_id = Column(String(50))
    draft_type = Column(String(50))  # 'RFI', 'RESPONSE', 'ACKNOWLEDGMENT'
    
    # Email details
    recipient = Column(String(255), nullable=False)
    subject = Column(Text, nullable=False)
    body = Column(Text, nullable=False)
    
    # Provider details (Outlook/Gmail)
    email_provider = Column(String(20))  # 'outlook' or 'gmail'
    provider_draft_id = Column(String(255))  # Draft ID from email provider
    
    # Status and metadata
    status = Column(String(50), default='DRAFT')  # 'DRAFT', 'SENT', 'DELETED'
    created_by = Column(String(50), default='RFQ_AGENT')
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    sent_at = Column(DateTime)
    
    # Link to original email
    in_reply_to_email_id = Column(String(255))

class FileLink(Base):
    __tablename__ = 'file_links'
    
    id = Column(Integer, primary_key=True)
    tender_id = Column(String(50))
    link_url = Column(Text, nullable=False)
    link_type = Column(String(50))
    download_status = Column(String(50))
    downloaded_filename = Column(String(255))
    error_message = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

class AgentHandover(Base):
    __tablename__ = 'agent_handovers'
    
    id = Column(Integer, primary_key=True)
    tender_id = Column(String(50))
    from_agent = Column(String(50), nullable=False)
    to_agent = Column(String(50), nullable=False)
    handover_data = Column(JSONB, nullable=False)
    status = Column(String(50))
    approved_by = Column(String(100))
    approved_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)

class AuditLog(Base):
    __tablename__ = 'audit_log'
    
    id = Column(Integer, primary_key=True)
    tender_id = Column(String(50))
    agent = Column(String(50))
    action = Column(String(100))
    details = Column(JSONB)
    user_id = Column(String(100))
    timestamp = Column(DateTime, default=datetime.utcnow)

class AssistantConversation(Base):
    __tablename__ = 'assistant_conversations'
    
    id = Column(Integer, primary_key=True)
    title = Column(String(255), default='New Conversation')
    created_at = Column(DateTime, default=datetime.utcnow)
    last_message_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class AssistantChat(Base):
    __tablename__ = 'assistant_chat'
    
    id = Column(Integer, primary_key=True)
    conversation_id = Column(Integer, ForeignKey('assistant_conversations.id'), nullable=True)
    role = Column(String(20), nullable=False) # 'user' or 'assistant'
    content = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)
