import sys
import os

# Set up path
sys.path.append(os.getcwd())

# Bcrypt Monkey Patch
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

def update_user():
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == 'user123').first()
        if user:
            print("Updating user123 password to user12345...")
            user.password_hash = get_password_hash('user12345')
            db.commit()
            print("Success!")
        else:
            print("User user123 not found!")
    finally:
        db.close()

if __name__ == "__main__":
    update_user()
