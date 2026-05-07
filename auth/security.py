from passlib.context import CryptContext
import bcrypt

# Standard password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password, hashed_password):
    """Verify a password against a hash"""
    try:
        # Try passlib first
        return pwd_context.verify(plain_password, hashed_password)
    except Exception:
        # Fallback to direct bcrypt for Python 3.12 compatibility
        if isinstance(plain_password, str):
            plain_password = plain_password.encode('utf-8')
        if isinstance(hashed_password, str):
            hashed_password = hashed_password.encode('utf-8')
        return bcrypt.checkpw(plain_password, hashed_password)

def get_password_hash(password):
    """Generate a password hash"""
    try:
        # Try passlib first
        return pwd_context.hash(password)
    except Exception:
        # Fallback to direct bcrypt for Python 3.12 compatibility
        salt = bcrypt.gensalt()
        if isinstance(password, str):
            password = password.encode('utf-8')
        return bcrypt.hashpw(password, salt).decode('utf-8')
