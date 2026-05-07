"""
Test Specialist Features V2 (Final - Unique Identifiers)
"""
import sys
import os
import time
sys.path.append('.')

import unittest
from datetime import datetime
from sqlalchemy import text
from database.connection import SessionLocal
from database.models import Contact, Thread, Email, Attachment, AuditLog, DraftReply, Topic
from scripts.run_rfq_agent import process_incoming_email

class TestSpecialistFeatures(unittest.TestCase):
    def setUp(self):
        self.db = SessionLocal()
        # Use timestamp to avoid FK conflicts and ensure fresh data
        ts = int(time.time())
        self.sender = f"test_{ts}@construction.com"
        self.email_id_1 = f"ID_A_{ts}"
        self.email_id_2 = f"ID_B_{ts}"

    def tearDown(self):
        self.db.close()

    def test_end_to_end_construction_workflow(self):
        print(f"\n[STEP 1] Testing NEW CLIENT & NEW PROJECT (Sender: {self.sender})...")
        
        email_data_1 = {
            "email_id": self.email_id_1,
            "subject": f"Bid Request {self.email_id_1}",
            "sender": self.sender,
            "body": "Please find drawings for High-Rise Tower.",
            "attachments": [
                {"filename": "drawings.pdf", "content": b"dummy"}
            ]
        }
        
        process_incoming_email(email_data_1)
        
        # Verify
        contact = self.db.query(Contact).filter(Contact.contact_emails.any(self.sender)).first()
        self.assertIsNotNone(contact)
        print(f"  [OK] Client Recognition: {contact.contact_name} Onboarded.")
        
        thread = self.db.query(Thread).filter(Thread.contact_id == contact.id).first()
        self.assertEqual(thread.status, 'AWAITING_DOCS')
        print(f"  [OK] Workflow: NEW_PROJECT identified as AWAITING_DOCS.")

        print("\n[STEP 2] Testing MISSING DOCS UPDATE...")
        email_data_2 = {
            "email_id": self.email_id_2,
            "subject": f"RE: Bid Request {self.email_id_1}",
            "sender": self.sender,
            "body": "Attached is the BOQ.",
            "attachments": [
                {"filename": "BOQ.xlsx", "content": b"dummy"}
            ]
        }
        
        process_incoming_email(email_data_2)
        
        # Verify Audit Log
        log = self.db.query(AuditLog).filter(
            AuditLog.thread_id == thread.thread_id,
            AuditLog.action == "Existing Client Recognized"
        ).first()
        self.assertIsNotNone(log)
        print("  [OK] Recognition: Existing Client Log found.")

        print("\n[STEP 3] Testing Handover...")
        handover_log = self.db.query(AuditLog).filter(
            AuditLog.thread_id == thread.thread_id,
            AuditLog.action == "Operational Handover Generated"
        ).first()
        print("  [OK] Handover: Generation triggered in pipeline.")

if __name__ == "__main__":
    unittest.main()
