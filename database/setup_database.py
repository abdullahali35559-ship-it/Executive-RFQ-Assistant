"""
Create Database and Tables for RFQ Agent
Run this script to setup the database
"""

import sys
sys.path.append('.')

from database.connection import engine, Base, SessionLocal
from database.models import Client, Tender, Document, Project
from sqlalchemy import text
import os
from dotenv import load_dotenv

load_dotenv()

def create_database():
    """Create all database tables"""
    
    print("=" * 60)
    print("RFQ Agent - Database Setup")
    print("=" * 60)
    
    print("\n[1/3] Checking database connection...")
    try:
        # Test connection
        db = SessionLocal()
        db.execute(text("SELECT 1"))
        db.close()
        print("✅ Database connection successful")
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        print("\nPlease ensure:")
        print("1. PostgreSQL is running")
        print("2. Database 'tender_system_db' exists")
        print("3. Credentials in .env are correct")
        return False
    
    print("\n[2/3] Creating tables...")
    try:
        # Create all tables
        Base.metadata.create_all(bind=engine)
        print("✅ Tables created successfully")
    except Exception as e:
        print(f"❌ Table creation failed: {e}")
        return False
    
    print("\n[3/3] Verifying tables...")
    try:
        db = SessionLocal()
        
        # Check each table
        tables = ['clients', 'projects', 'tenders', 'documents']
        for table in tables:
            result = db.execute(text(f"SELECT COUNT(*) FROM {table}"))
            count = result.fetchone()[0]
            print(f"  ✅ {table}: {count} records")
        
        db.close()
    except Exception as e:
        print(f"❌ Verification failed: {e}")
        return False
    
    print("\n" + "=" * 60)
    print("✅ DATABASE SETUP COMPLETE!")
    print("=" * 60)
    print("\nNext steps:")
    print("1. Database is ready to use")
    print("2. Run: .\\process_emails.bat")
    print("3. Data will be saved to database + files")
    print("\n")
    
    return True

if __name__ == "__main__":
    success = create_database()
    
    if not success:
        print("\n⚠️  Setup failed. Please fix errors and try again.")
        sys.exit(1)
    else:
        print("🎉 You're all set!")
        sys.exit(0)
