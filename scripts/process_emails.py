import sys
import io
sys.path.append('.')

from agents.rfq_agent.email_fetcher import EmailFetcher
from agents.rfq_agent.rfi_generator import RFIGenerator
from scripts.run_rfq_agent import process_tender_email, log_progress
import time
from datetime import datetime
import email.utils
from database.models import Email, AuditLog, Tender, DraftEmail
from database.connection import SessionLocal


def process_email_batch():
    """
    Fetch and process tender emails from ALL configured providers
    """
    from config.settings import EMAIL_PROVIDERS
    
    print("=" * 60)
    print("EMAIL MONITORING - RFQ Agent")
    print("=" * 60)
    print(f"Providers: {', '.join(EMAIL_PROVIDERS)}")
    print()

    db = SessionLocal()
    try:
        log_progress(db, "BATCH", "Starting Email Processing", {"providers": EMAIL_PROVIDERS})
    finally:
        db.close()
    
    total_processed = 0
    processed_email_ids = set()  # Track already processed emails across providers
    
    # Process each provider
    for provider in EMAIL_PROVIDERS:
        print(f"\n{'=' * 60}")
        print(f"CHECKING: {provider.upper()}")
        print(f"{'=' * 60}\n")

        db = SessionLocal()
        try:
            log_progress(db, "BATCH", f"Checking provider: {provider}")
        finally:
            db.close()
        # Initialize email fetcher for this provider
        try:
            fetcher = EmailFetcher(provider=provider)
        except ValueError as e:
            print(f"[WARNING] Skipping {provider}: {e}\n")
            continue
        
        if not fetcher.connect():
            print(f"[ERROR] Could not connect to {provider}")
            continue
        
        try:
            # Fetch tender emails
            print(f"Fetching tender emails from {provider}...")
            emails = fetcher.fetch_tender_emails(limit=50)
            
            if not emails:
                print(f"No tender emails from {provider}")
                continue
            
            print(f"\nProcessing {len(emails)} email(s) from {provider}...\n")
            db = SessionLocal()
            try:
                log_progress(db, "BATCH", f"Found {len(emails)} emails in {provider}")
            finally:
                db.close()
            
            # Save new emails to DB and process them
            for idx, email_data in enumerate(emails, 1):
                email_id = email_data['email_id']
                
                # Skip if already processed in this batch (cross-provider dedup)
                if email_id in processed_email_ids:
                    print(f"\n[SKIP] Email already processed in this batch: {email_data['subject'][:50]}...")
                    continue
                
                # Check if already exists in database
                db = SessionLocal()
                try:
                    existing = db.query(Email).filter(Email.email_id == email_id).first()
                    if existing and existing.processed:
                        print(f"\n[SKIP] Email already processed previously: {email_data['subject'][:50]}...")
                        # UPDATE: Even if skipped, update the tender's updated_at so it moves to top of list
                        if existing.tender_id:
                            tender = db.query(Tender).filter(Tender.tender_id == existing.tender_id).first()
                            if tender:
                                tender.updated_at = datetime.utcnow()
                                db.commit()
                                
                                # Also check if it's now complete and cleanup OLD drafts if so
                                try:
                                    rfi_gen = RFIGenerator()
                                    completeness = rfi_gen.check_completeness(existing.tender_id)
                                    if not completeness.get('missing') and not completeness.get('incorrect'):
                                        # Delete old drafts if documents are now complete
                                        old_drafts = db.query(DraftEmail).filter(
                                            DraftEmail.tender_id == existing.tender_id,
                                            DraftEmail.status == 'DRAFT'
                                        ).all()
                                        if old_drafts:
                                            print(f"   [OK] Tender {existing.tender_id} now complete. Deleting {len(old_drafts)} stale RFI draft(s).")
                                            for od in old_drafts:
                                                db.delete(od)
                                            db.commit()
                                except Exception as re:
                                    print(f"   [!] Error during skipped email completeness check: {re}")
                        
                        processed_email_ids.add(email_id)
                        continue
                    
                    # Save to DB if not exists (is_tender=False until AI confirms)
                    if not existing:
                        received_at = None
                        if email_data.get('date'):
                            try:
                                dt = email.utils.parsedate_to_datetime(email_data['date'])
                                received_at = dt
                            except:
                                received_at = datetime.utcnow()
                        
                        new_email = Email(
                            email_id=email_id,
                            subject=email_data['subject'],
                            sender=email_data['sender'],
                            body=email_data['body'],
                            received_at=received_at or datetime.utcnow(),
                            is_tender=False,  # Will be updated after AI detection
                            processed=False,
                            detection_confidence=0.0
                        )
                        db.add(new_email)
                        db.commit()
                finally:
                    db.close()
                
                # Process through RFQ Agent
                print(f"\n{'=' * 60}")
                print(f"Processing Email {idx}/{len(emails)} ({provider})")
                print(f"{'=' * 60}")
                print(f"Subject: {email_data['subject']}")
                print(f"From: {email_data['sender']}")
                print(f"Attachments: {len(email_data['attachments'])}")
                print()
                
                try:
                    result = process_tender_email(email_data)
                    
                    # Mark as processed in DB ONLY IF successful reaching here
                    db = SessionLocal()
                    try:
                        db_email = db.query(Email).filter(Email.email_id == email_id).first()
                        if db_email:
                            db_email.processed = True
                            if result:
                                db_email.is_tender = True
                                db_email.detection_confidence = result.get('confidence', 0.95)
                                db_email.tender_id = result.get('tender_id')
                            db.commit()
                            
                            # Move to processed folder (Only for Tenders that succeeded)
                            if result:
                                print(f"\n[OK] Email processed successfully!")
                                print(f"   Tender ID: {result.get('tender_id')}")
                                print(f"   Status: {result.get('handover_status')}")
                                fetcher.move_to_processed(email_data)
                                total_processed += 1
                            else:
                                print(f"\n[--] Not a tender email, skipped.")
                                # Keep UNREAD in provider based on USER request:
                                print("   (Leaving email as UNREAD in provider)")
                    finally:
                        db.close()
                    
                    processed_email_ids.add(email_id)
                    
                except Exception as e:
                    print(f"\n[ERROR] Error processing email: {e}")
                    import traceback
                    traceback.print_exc()
                    # CRITICAL: We DO NOT set processed=True here, so it will retry next time
            
        finally:
            fetcher.disconnect()
    
    db = SessionLocal()
    try:
        log_progress(db, "BATCH", "Batch processing complete", {"total": total_processed})
    finally:
        db.close()
        
    print(f"\n{'=' * 60}")
    print(f"[OK] Batch processing complete")
    print(f"Total tender emails processed: {total_processed}")
    print(f"{'=' * 60}\n")


if __name__ == "__main__":
    print("\nStarting email monitoring...\n")
    process_email_batch()
