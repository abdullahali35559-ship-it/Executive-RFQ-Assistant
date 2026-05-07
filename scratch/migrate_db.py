
import sys
import os
from sqlalchemy import create_engine, text

# Add parent directory to path to import config
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.settings import DATABASE_URL

def fix_database():
    print(f"Connecting to {DATABASE_URL}...")
    engine = create_engine(DATABASE_URL)
    
    with engine.connect() as conn:
        print("Adding message_id and in_reply_to to emails table...")
        try:
            # Check if columns exist first
            conn.execute(text("ALTER TABLE emails ADD COLUMN IF NOT EXISTS message_id VARCHAR(255)"))
            conn.execute(text("ALTER TABLE emails ADD COLUMN IF NOT EXISTS in_reply_to VARCHAR(255)"))
            
            # Create indexes
            conn.execute(text("CREATE INDEX IF NOT EXISTS ix_emails_message_id ON emails (message_id)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS ix_emails_in_reply_to ON emails (in_reply_to)"))
            
            conn.commit()
            print("DONE: Database schema updated successfully.")
        except Exception as e:
            print(f"Error updating database: {e}")

if __name__ == "__main__":
    fix_database()
