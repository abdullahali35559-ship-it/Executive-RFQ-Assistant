import sys
import os

# Set up path
sys.path.append(os.getcwd())

# Bcrypt Monkey Patch (Mirroring main.py)
try:
    import bcrypt
    if not hasattr(bcrypt, "__about__"):
        class About: pass
        about = About()
        about.__version__ = "4.0.0"
        bcrypt.__about__ = about
except ImportError: pass

from config.database import SessionLocal
from database.models import User
from auth.security import get_password_hash

def reset_users():
    db = SessionLocal()
    try:
        targets = ["user123", "user12345"]
        for email in targets:
            user = db.query(User).filter(User.email == email).first()
            if user:
                print(f"Resetting password for {email}...")
                user.password_hash = get_password_hash(email) # password is same as username
            else:
                print(f"Creating user {email}...")
                db.add(User(
                    email=email,
                    password_hash=get_password_hash(email),
                    role="user",
                    full_name=f"Standard User {email}"
                ))
        db.commit()
        print("Success!")
    finally:
        db.close()

if __name__ == "__main__":
    reset_users()
