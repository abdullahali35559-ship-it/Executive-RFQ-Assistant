import os
import sys
import shutil
from sqlalchemy import text
from sqlalchemy.orm import Session

# Add project root to path
sys.path.append('.')

from database.connection import SessionLocal
from config.settings import STORAGE_PATH

def clear_all_data():
    """
    CLEANUP SCRIPT: Wipes all business data while keeping user accounts.
    """
    print("=== RFI SYSTEM DATA CLEANUP STARTED ===")
    db = SessionLocal()
    
    try:
        # 1. Clear Intelligent Data Tables
        # Using CASCADE-style deletion order
        tables_to_clear = [
            "assistant_chat",
            "assistant_conversations",
            "audit_log",
            "followup_tasks",
            "draft_replies",
            "attachments",
            "email_tags",
            "thread_tags",
            "emails",
            "threads",
            "topics",
            "contacts",
            "tags"
        ]
        
        print("\nStep 1: Clearing database records...")
        for table in tables_to_clear:
            try:
                db.execute(text(f"DELETE FROM {table}"))
                print(f"  [√] Cleared table: {table}")
            except Exception as e:
                print(f"  [!] Skip/Error in {table}: {e}")
        
        # 2. Reset User Intelligence Settings (Keep the Login alive)
        print("\nStep 2: Resetting User Style Profiles (Keeping Logins)...")
        db.execute(text("""
            UPDATE users 
            SET brand_voice = NULL, 
                writing_style_guide = NULL, 
                last_style_sync = NULL, 
                custom_instructions = NULL
        """))
        print("  [√] All User Style Profiles reset to factory settings.")

        db.commit()
        print("\nStep 3: Committing database changes...")

        # 4. Clear Physical Files
        print(f"\nStep 4: Purging physical storage in {STORAGE_PATH}...")
        if os.path.exists(STORAGE_PATH):
            # We don't delete the folder itself, just contents
            for filename in os.listdir(STORAGE_PATH):
                file_path = os.path.join(STORAGE_PATH, filename)
                try:
                    if os.path.isfile(file_path) or os.path.islink(file_path):
                        os.unlink(file_path)
                    elif os.path.is_dir(file_path):
                        shutil.rmtree(file_path)
                    print(f"  [√] Deleted file/folder: {filename}")
                except Exception as e:
                    print(f"  [!] Failed to delete {file_path}: {e}")
        
        print("\n=== CLEANUP COMPLETE: SYSTEM IS NOW FRESH FOR CLIENT TESTING ===")
        print("Login credentials remain active.")

    except Exception as e:
        print(f"\n[CRITICAL ERROR] Cleanup failed: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    # We use a simple check for VPS execution
    clear_all_data()
