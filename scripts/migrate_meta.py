
from sqlalchemy import text
from database.connection import engine

def migrate():
    print("Migrating database...")
    with engine.connect() as conn:
        conn.execute(text("ALTER TABLE threads ADD COLUMN IF NOT EXISTS meta_data JSONB"))
        conn.commit()
    print("Migration complete.")

if __name__ == "__main__":
    migrate()
