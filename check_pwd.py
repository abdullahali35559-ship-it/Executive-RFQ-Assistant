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

from passlib.context import CryptContext
from auth.security import verify_password

def check():
    ctx = CryptContext(schemes=["bcrypt"])
    # Get backend safely
    try:
        backend = ctx.handler()._get_backend()
    except:
        backend = "unknown"
    print(f"Backend: {backend}")
    
    # Check a known hash from my previous DB check
    stored_hash = "$2b$12$sGBVwIXyyBibp/5ZDB5vxe17y14BL4WJWc0SaK8DwujWi8CMQc3jC"
    result = verify_password("user123", stored_hash)
    print(f"Verify 'user123': {result}")

if __name__ == "__main__":
    check()
