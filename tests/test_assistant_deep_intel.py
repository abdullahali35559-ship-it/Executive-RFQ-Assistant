
from sqlalchemy.orm import Session
from database.models import User, Email, Contact, Attachment
from agents.executive.assistant import ExecutiveAssistant
from config.database import SessionLocal
from datetime import datetime, timedelta

def test_deep_intelligence():
    db = SessionLocal()
    assistant = ExecutiveAssistant(db)
    
    print("\n--- TEST 1: GREETING & NO DATA CHECK ---")
    # Simulate greeting with no data (if DB was empty, but we know it has data)
    print(assistant.answer_query("Hello"))
    
    print("\n--- TEST 2: EXECUTIVE BRIEFING & RELATIONSHIP ---")
    # Simulate broad query
    response = assistant.answer_query("What happened in my emails in the last 3 days?")
    print(response)
    
    print("\n--- TEST 3: BEHAVIORAL PATTERNS ---")
    # Update user instructions to test behavioral patterns
    user = db.query(User).first()
    if user:
        user.custom_instructions = "I am very busy this week. Do not suggest any meetings on Friday after 3 PM. Priority should be given to client 'Lancers Tech'."
        db.commit()
        
    response = assistant.answer_query("Summarize my workspace and check for any Friday meetings.")
    print(response)
    
    db.close()

if __name__ == "__main__":
    test_deep_intelligence()
