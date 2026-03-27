"""
RFQ Agent - Main Workflow Execution
Complete email → handover workflow
"""

import sys
sys.path.append('.')

from agents.rfq_agent.email_detector import EmailDetector
from agents.rfq_agent.document_classifier import DocumentClassifier
from agents.rfq_agent.file_manager import FileManager, generate_tender_id
from agents.rfq_agent.rfi_generator import RFIGenerator
from agents.rfq_agent.draft_manager import DraftManager
from agents.rfq_agent.metadata_extractor import MetadataExtractor
from agents.rfq_agent.handover_generator import HandoverGenerator
from agents.rfq_agent.client_matcher import ClientMatcher
from agents.rfq_agent.project_matcher import ProjectMatcher
from agents.rfq_agent.document_versioner import DocumentVersioner
from agents.rfq_agent.cloud_link_detector import CloudLinkDetector
from agents.rfq_agent.cloud_file_downloader import CloudFileDownloader
from database.connection import SessionLocal
import re
import os
import json
import zipfile
import io
from typing import Dict, List
from datetime import datetime
from database.models import Tender, Document, Email, DraftEmail, AuditLog, FileLink

# Set to False after client video presentation
DEMO_MODE = False

def sanitize_filename(filename: str) -> str:
    """
    Remove illegal characters for Windows filenames and ensure safe path joining
    """
    if not filename:
        return "unnamed_file"
    
    # Replace characters not allowed in Windows filenames: \ / : * ? " < > |
    s = re.sub(r'[\\/:*?"<>|]', '_', filename)
    
    # Also remove common problematic characters
    s = re.sub(r'[\s]+', ' ', s).strip() # normalize whitespace
    
    return s

def log_progress(db, tender_id, action, details=None):
    """Log agent progress to the audit_log table for UI tracking"""
    try:
        log = AuditLog(
            tender_id=tender_id,
            agent="RFQ_AGENT",
            action=f"PROGRESS: {action}",
            details=details or {},
            timestamp=datetime.utcnow()
        )
        db.add(log)
        db.commit()
    except Exception as e:
        print(f"  [!] Failed to log progress: {e}")
        db.rollback()

def process_tender_email(email_data: Dict):
    """
    Complete RFQ Agent workflow
    """
    
    print("=== RFQ AGENT STARTED ===\n")
    
    # Step 1: Detect tender email
    print("Step 1: Detecting tender email...")
    detector = EmailDetector()
    
    detection = detector.detect_tender_email(
        email_id=email_data['email_id'],
        subject=email_data['subject'],
        sender=email_data['sender'],
        body=email_data['body'],
        attachments=email_data.get('attachments', [])
    )
    
    if not detection['is_tender']:
        print("❌ Not a tender email. IGNORED.")
        return None
    
    print(f"✅ Tender detected (confidence: {detection['confidence']:.2f})")
    
    # Database session
    db_session = SessionLocal()
    
    try:
        log_progress(db_session, email_data['email_id'], "Agent Started", {"subject": email_data['subject']})
        # Step 2: Match or create client
        print("\nStep 2: Identifying client...")
        client_matcher = ClientMatcher()
        client = client_matcher.find_or_create_client(
            email_sender=email_data['sender'],
            email_body=email_data['body'],
            session=db_session
        )
        print(f"✅ Client: {client.client_name} (ID: {client.id})")
        
        # Step 3: Match or create project
        print("\nStep 3: Matching project...")
        project_matcher = ProjectMatcher()
        project = project_matcher.find_matching_project(
            client_id=client.id,
            project_data={
                'subject': email_data['subject'],
                'body': email_data['body'],
                'attachments': email_data.get('attachments', [])
            },
            session=db_session
        )
        
        # Determine if this is an update or new project
        is_update = project is not None
        
        if is_update:
            tender_id = project.tender_id
            print(f"✅ Existing project found: {project.project_name}")
            print(f"   Using Tender ID: {tender_id}")
        else:
            # Generate new tender ID
            tender_id = generate_tender_id()
            print(f"✅ New project - Generated Tender ID: {tender_id}")
            
            # Extract project info
            project_ref = project_matcher.extract_project_reference({
                'subject': email_data['subject'],
                'body': email_data['body']
            })
            project_name = email_data['subject']
            
            # Create new project
            project = project_matcher.create_new_project(
                client_id=client.id,
                tender_id=tender_id,
                project_name=project_name,
                project_reference=project_ref,
                session=db_session
            )
            
            # Create corresponding Tender record (for dashboard visibility)
            from database.models import Tender
            from datetime import datetime
            new_tender = Tender(
                tender_id=tender_id,
                status='PROCESSING',
                client_id=client.id,
                project_id=project.id,
                client_name=client.client_name,
                project_name=project.project_name,
                tender_reference=project_ref or tender_id,
                created_at=datetime.utcnow()
            )
            db_session.add(new_tender)
        
        # Mark email as processed in database
        from database.models import Email
        email_record = db_session.query(Email).filter(Email.email_id == email_data['email_id']).first()
        if email_record:
            email_record.processed = True
            email_record.tender_id = tender_id
            
        # Commit NOW so dashboard sees the new Tender and updated Email status
        db_session.commit()
        
        # Step 4: Setup folder structure
        # ...
        log_progress(db_session, tender_id, "Setting up folders")
        file_manager = FileManager()
        tender_folder = file_manager.create_tender_folder(tender_id)
        print(f"✅ Folder: {tender_folder}")
        
        # Step 4.5: Download files from cloud links
        print("\nStep 4.5: Checking for cloud storage links...")
        cloud_detector = CloudLinkDetector()
        cloud_downloader = CloudFileDownloader()
        from database.models import FileLink
        
        cloud_links = cloud_detector.detect_links(email_data.get('body', ''))
        
        if cloud_links:
            print(f"  Found {len(cloud_links)} cloud link(s)")
            
            for link in cloud_links:
                provider = link['provider'].value
                url = link['url']
                
                print(f"  [->] {provider.upper()}: {url[:50]}...")
                
                try:
                    if provider in ['onedrive', 'sharepoint']:
                        downloaded_files = cloud_downloader.download_from_onedrive(
                            share_url=url,
                            save_dir=tender_folder
                        )
                    elif provider == 'google_drive':
                        file_id = link.get('file_id')
                        if file_id:
                            downloaded_files = cloud_downloader.download_from_google_drive(
                                drive_url=url,
                                file_id=file_id,
                                save_dir=tender_folder
                            )
                        else:
                            print(f"    [!] Could not extract file ID from link")
                            downloaded_files = []
                    else:
                        print(f"    [!] {provider.upper()} not yet supported")
                        downloaded_files = []
                    
                    if downloaded_files:
                        # Add downloaded files to attachments for classification
                        for file_path in downloaded_files:
                            filename = os.path.basename(file_path)
                            with open(file_path, 'rb') as f:
                                content = f.read()
                            
                            if 'cloud_files' not in email_data:
                                email_data['cloud_files'] = []
                            
                            email_data['cloud_files'].append({
                                'filename': filename,
                                'content': content,
                                'source': provider
                            })
                
                except Exception as e:
                    error_msg = str(e)
                    print(f"    [X] Error downloading from {provider}: {error_msg}")
                    
                    # Save error to database for RFI reporting
                    try:
                        file_link = FileLink(
                            tender_id=tender_id,
                            link_url=url,
                            link_type=provider,
                            download_status='FAILED',
                            error_message=error_msg
                        )
                        db_session.add(file_link)
                        db_session.commit()
                    except:
                        db_session.rollback()
        else:
            print("  No cloud links found")
        
        # Step 5: Classify and store documents with versioning
        print("\nStep 5: Classifying documents...")
        log_progress(db_session, tender_id, "Classifying documents", {"count": len(email_data.get('attachments', [])) + len(email_data.get('cloud_files', []))})
        
        classifier = DocumentClassifier()
        versioner = DocumentVersioner()
        documents = []
        
        # Create temp directory if needed
        os.makedirs("./temp", exist_ok=True)
        
        # Combine email attachments and cloud-downloaded files
        all_files = []
        
        def extract_recursive(filename, content, source):
            """Helper to extract zips and handle nested files"""
            if filename.lower().endswith('.zip'):
                print(f"  [Zip] Extracting: {filename}")
                try:
                    with zipfile.ZipFile(io.BytesIO(content)) as z:
                        for zinfo in z.infolist():
                            if zinfo.is_dir(): continue
                            with z.open(zinfo) as f:
                                z_content = f.read()
                                extract_recursive(zinfo.filename, z_content, f"{source}/zip")
                except Exception as ze:
                    print(f"  [X] Zip error {filename}: {ze}")
                    # If zip fails, we might still want to keep it as a file? 
                    # Usually signifies corruption, but let's just log.
            else:
                safe_name = sanitize_filename(os.path.basename(filename))
                all_files.append({
                    'filename': safe_name,
                    'original_name': filename,
                    'content': content,
                    'source': source
                })

        # Add email attachments (with zip support)
        for attachment in email_data.get('attachments', []):
            extract_recursive(attachment['filename'], attachment['content'], 'email')
        
        # Add cloud-downloaded files (with zip support)
        for cloud_file in email_data.get('cloud_files', []):
            extract_recursive(cloud_file['filename'], cloud_file['content'], cloud_file['source'])
        
        for i, file_info in enumerate(all_files, 1):
            # Save file temporarily for classification
            # CRITICAL: Sanitize again just in case, and use absolute path if possible
            filename = file_info['filename']
            temp_path = os.path.join(os.getcwd(), "temp", filename)
            
            log_progress(db_session, tender_id, f"Processing file {i}/{len(all_files)}", {"filename": filename})
            
            with open(temp_path, 'wb') as f:
                f.write(file_info['content'])
            
            # Classify
            classification = classifier.classify_document(
                filename=filename,
                file_path=temp_path
            )
            
            # Check for duplicate by hash
            import hashlib
            file_hash = hashlib.sha256(file_info['content']).hexdigest()
            
            existing = versioner.check_if_duplicate(
                tender_id=tender_id,
                file_hash=file_hash,
                session=db_session
            )
            
            if existing:
                print(f"  ⚠️  {file_info['filename']} → Duplicate (skipped)")
                # Clean up temp file  
                os.remove(temp_path)
                continue
            
            # Get version number
            version = versioner.get_latest_version(
                tender_id, 
                file_info['filename'],
                db_session
            ) + 1
            
            # Save to proper category with versioning
            save_result = file_manager.save_file(
                file_data=file_info['content'],
                tender_id=tender_id,
                category=classification['category'],
                original_filename=file_info['filename'],
                version=version
            )
            
            if save_result['status'] == "QUARANTINED":
                print(f"  ❌ {filename} → MALWARE DETECTED! (Quarantined)")
                log_progress(db_session, tender_id, "Malware Detected", {"filename": filename})
                # Cleanup classification temp file
                if os.path.exists(temp_path):
                    os.remove(temp_path)
                continue

            # Save document record to database
            doc = Document(
                tender_id=tender_id,
                filename=save_result['versioned_filename'],
                original_filename=file_info['filename'],
                file_path=save_result['path'],
                file_hash=file_hash,
                file_size_bytes=save_result['size'],
                category=classification['category'],
                classification_confidence=classification['confidence'],
                version=version
            )
            db_session.add(doc)
            
            # Immediate verification commit
            try:
                db_session.commit()
                print(f"  [OK] Registered in database: {save_result['versioned_filename']}")
            except Exception as e:
                print(f"  [!] Database registration failed for {file_info['filename']}: {e}")
                db_session.rollback()
                # Move to repair folder
                repair_dir = os.path.join(STORAGE_PATH, "repair_pending", tender_id)
                os.makedirs(repair_dir, exist_ok=True)
                import shutil
                shutil.copy(save_result['path'], os.path.join(repair_dir, save_result['versioned_filename']))
                print(f"      File copied to repair_pending for sync.")
            
            documents.append({
                "filename": save_result['versioned_filename'],
                "original_filename": file_info['filename'],
                "file_path": save_result['path'],
                "category": classification['category'],
                "confidence": classification['confidence'],
                "file_hash": save_result['hash'],
                "version": version
            })
            
            version_str = f"v{version}" if version > 1 else "v1"
            # Clean up temp file AFTER successful processing
            if os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except:
                    pass
        
        db_session.commit()
    
        # Step 6: Check completeness & generate consolidated RFIs
        print("\nStep 6: Checking completeness...")
        rfi_gen = RFIGenerator()
        draft_manager = DraftManager()
        completeness = rfi_gen.check_completeness(tender_id, documents)
        
        missing_docs = completeness.get('missing', [])
        incorrect_docs = completeness.get('incorrect', [])
        irrelevant_files = completeness.get('irrelevant', [])
        
        rfi_drafts = []
        if missing_docs or incorrect_docs or irrelevant_files:
            print(f"  ⚠️  Missing {len(missing_docs)}, Incorrect {len(incorrect_docs)}, and Irrelevant {len(irrelevant_files)} document(s)")
            
            # Collect all attachments (classified documents) for the RFI draft
            all_attachments = [d['file_path'] for d in documents]
            
            # Generate ONE consolidated RFI draft
            rfi_draft = rfi_gen.generate_consolidated_rfi_draft(
                tender_id=tender_id,
                missing_categories=missing_docs,
                incorrect_categories=incorrect_docs,
                irrelevant_files=irrelevant_files,
                tender_metadata={
                    'client_name': client.client_name if client else email_data['sender'].split('@')[0],
                    'tender_reference': tender_id
                }
            )
            
            print(f"  [->] Consolidated RFI Generated: {rfi_draft['rfi_id']}")
            
            # Save as ONE draft email
            provider = email_data.get('provider', 'gmail').lower()
            sender_email = email_data['sender']
            
            try:
                draft_result = draft_manager.create_draft(
                    provider=provider,
                    to=sender_email,
                    subject=rfi_draft['subject'],
                    body=rfi_draft['body'],
                    attachments=all_attachments
                )
                
                if draft_result['success']:
                    rfi_draft['draft_id'] = draft_result['draft_id']
                    print(f"       ✅ Consolidated draft saved to {provider.upper()} with {len(all_attachments)} attachments")
                    
                    # Save to database
                    new_draft = DraftEmail(
                        tender_id=tender_id,
                        draft_type='RFI_CONSOLIDATED',
                        recipient=sender_email,
                        subject=rfi_draft['subject'],
                        body=rfi_draft['body'],
                        email_provider=provider,
                        provider_draft_id=draft_result['draft_id'],
                        status='DRAFT',
                        in_reply_to_email_id=email_data['email_id']
                    )
                    db_session.add(new_draft)
                    db_session.commit()
                else:
                    print(f"       ⚠️  Consolidated draft save failed: {draft_result.get('error')}")
            except Exception as e:
                print(f"       ⚠️  Consolidated draft save failed: {e}")
            
            rfi_drafts.append(rfi_draft)
        else:
            print("  ✅ All required documents present and correct")
        
        # Step 7: Extract metadata
        print("\nStep 7: Extracting metadata...")
        extractor = MetadataExtractor()
        metadata = extractor.extract_metadata(tender_id, email_data, documents)
        print(f"  ✅ Client: {metadata.get('client_name')}")
        print(f"  ✅ Project: {metadata.get('project_name')}")
        
        # Step 8: Generate handover
        print("\nStep 8: Generating handover...")
        handover_gen = HandoverGenerator()
        
        # Get TOTAL document count from DB for this tender
        total_docs_in_db = db_session.query(Document).filter(Document.tender_id == tender_id).count()

        handover = handover_gen.create_handover(
            tender_id=tender_id,
            metadata=metadata,
            documents=documents,
            rfi_drafts=rfi_drafts
        )
        
        # Overwrite summary count with true DB count
        handover['rfq_agent_summary']['total_documents'] = total_docs_in_db
        
        print(f"  ✅ Handover JSON created")
        
        print("\n=== RFQ AGENT COMPLETE ===")
        log_progress(db_session, tender_id, "Agent Completed", {"status": handover['handover_status']})
        
        # Explicitly update tender.updated_at to move it to the top of lists
        tender_obj = db_session.query(Tender).filter(Tender.tender_id == tender_id).first()
        if tender_obj:
            tender_obj.updated_at = datetime.utcnow()
            db_session.commit()
        
        print(f"Status: {handover['handover_status']}")
        print(f"Documents: {handover['rfq_agent_summary']['total_documents']}")
        print(f"RFI Drafts: {handover['rfq_agent_summary']['rfi_drafts_generated']}")
        
        # Save handover to file
        with open(f"./storage/tenders/{tender_id}/08_Output/handover.json", 'w') as f:
            json.dump(handover, f, indent=2)
        
        return handover
    
    finally:
        db_session.close()

# Example usage
if __name__ == "__main__":
    # Sample email for testing
    sample_email = {
        "email_id": "test_001",
        "subject": "RFQ-NEOM-2026-001 - MEP Package",
        "sender": "tenders@neom.com",
        "body": "Please submit your opinion for MEP works at Zone A...",
        "attachments": [
            {
                "filename": "Tender_Instructions.pdf",
                "content": b"Sample PDF content..."
            }
            # Add more attachments for testing
        ]
    }
    
    print("Testing RFQ Agent with sample email...\n")
    result = process_tender_email(sample_email)
    
    if result:
        print("\n✅ Workflow completed successfully!")
