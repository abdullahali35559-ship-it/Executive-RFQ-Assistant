
import sys
import os
sys.path.append('.')

from scripts.run_rfq_agent import process_incoming_email
from database.connection import SessionLocal
from database.models import Thread, DraftReply, Email, Attachment, AuditLog
import shutil
import json

def setup_test_environment():
    """Cleanup old test data"""
    db = SessionLocal()
    # Delete previous test threads
    db.query(Thread).filter(Thread.thread_id.like("TEST-TENDER-%")).delete(synchronize_session=False)
    db.commit()
    db.close()
    
    # Ensure temp dir exists
    os.makedirs("./temp", exist_ok=True)

def run_specialist_test():
    print("STARTING SPECIALIST FEATURE TEST\n")
    
    # 1. Prepare Mock Data
    # Custom test string for our scanner
    eicar_content = b"This is a test file containing RF_MALWARE_TEST_STRING for safety checks."
    
    mock_email = {
        "email_id": f"test_specialist_{int(os.path.getmtime('.'))}",
        "subject": "URGENT: RFQ for NEOM Villa Project - Site A12",
        "sender": "procurement@neom.com",
        "body": """
        Dear Team,
        
        Please find attached the RFQ for the NEOM Villa Project in Tabuk, Saudi Arabia.
        The submission deadline is May 25th, 2026.
        
        We have attached the Scope of Work and Drawings. Please note the BOQ will be sent later.
        Also, we included a 'System Check' file which might be flagged by some scanners.
        
        Regards,
        NEOM Procurement
        """,
        "attachments": [
            {"filename": "Scope_of_Work.pdf", "content": b"PDF content for scope..."},
            {"filename": "Site_Drawings.pdf", "content": b"PDF content for drawings..."},
            {"filename": "virus_test.txt", "content": eicar_content} # Should be quarantined
        ],
        "provider": "gmail"
    }
    
    # 2. Execute Workflow
    print("--- STEP 1: Executing Process Incoming Email ---")
    result = process_incoming_email(mock_email)
    
    if result.get('status') == 'SUCCESS':
        thread_id = result['thread_id']
        print(f"\nWorkflow SUCCESS. Thread ID: {thread_id}")
        
        # 3. Verify Database Records
        db = SessionLocal()
        try:
            # A. Check Malware Quarantine
            print("\n--- VERIFICATION: Malware Scanner ---")
            logs = db.query(AuditLog).filter(AuditLog.thread_id == thread_id, AuditLog.action == "Malware Detected").all()
            if logs:
                print(f"SUCCESS: Malware detected and logged: {logs[0].details}")
            else:
                print("FAIL: Malware was NOT detected.")

            # B. Check Metadata Extraction
            print("\n--- VERIFICATION: Deep Metadata ---")
            thread = db.query(Thread).filter(Thread.thread_id == thread_id).first()
            meta = thread.meta_data or {}
            print(f"Extracted Location: {meta.get('location')}")
            print(f"Extracted Deadline: {meta.get('submission_deadline')}")
            
            loc = str(meta.get('location', ''))
            if "Tabuk" in loc or "Saudi Arabia" in loc:
                print("SUCCESS: Deep Location metadata extracted correctly.")
            else:
                print("FAIL: Deep metadata extraction failed or inaccurate.")

            # C. Check RFI Generation (Since BOQ was missing)
            print("\n--- VERIFICATION: RFI Generator ---")
            rfi_drafts = db.query(DraftReply).filter(DraftReply.thread_id == thread_id, DraftReply.draft_type == 'CLARIFICATION').all()
            if rfi_drafts:
                print(f"SUCCESS: Found {len(rfi_drafts)} RFI draft(s). Subject: {rfi_drafts[0].subject}")
                if "BOQ" in rfi_drafts[0].body or "Bill of Quantities" in rfi_drafts[0].body:
                    print("SUCCESS: RFI specifically asks for missing BOQ.")
            else:
                print("FAIL: RFI Draft was NOT generated despite missing BOQ.")

            # D. Check Handover Generation
            print("\n--- VERIFICATION: Handover Packet ---")
            # Correct path from run_rfq_agent logic: ./storage/emails/{thread_id}/handover_packet.json
            storage_path = f"./storage/emails/{thread_id}/handover_packet.json"
            if os.path.exists(storage_path):
                print(f"SUCCESS: Handover packet found at {storage_path}")
            else:
                print("FAIL: Handover packet was NOT generated.")
                
        finally:
            db.close()
    else:
        print(f"Workflow FAILED: {result.get('reason')}")

if __name__ == "__main__":
    setup_test_environment()
    run_specialist_test()
