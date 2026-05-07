
import requests
import json

# Try to get stats from the running server
try:
    # We need a token. Let's try to get one for 'admin@123'
    # Actually, let's bypass auth if we can or just check the code again.
    # Since I can't easily get a token without password, I'll check the DB directly again but with MORE detail.
    from config.database import SessionLocal
    from database.models import Thread, Email, Contact, DraftReply
    db = SessionLocal()
    print("--- DB RAW CHECK ---")
    threads = db.query(Thread).all()
    print(f"Threads count: {len(threads)}")
    for t in threads:
        print(f"Thread: {t.thread_id}, Status: {t.status}, Subject: {t.subject}")
    
    emails = db.query(Email).all()
    print(f"Emails count: {len(emails)}")
    
    db.close()
except Exception as e:
    print(f"Error: {e}")
