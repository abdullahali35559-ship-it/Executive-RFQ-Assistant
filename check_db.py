
from config.database import SessionLocal
from database.models import Thread, Email, Contact, DraftReply

db = SessionLocal()
try:
    print(f"Threads: {db.query(Thread).count()}")
    print(f"Emails: {db.query(Email).count()}")
    print(f"Contacts: {db.query(Contact).count()}")
    print(f"Drafts: {db.query(DraftReply).count()}")
finally:
    db.close()
