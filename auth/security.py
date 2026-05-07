from datetime import datetime, timedelta
from typing import Optional, Union, Any
from jose import jwt, JWTError
from passlib.context import CryptContext
import bcrypt
import os
from dotenv import load_dotenv

load_dotenv()

# Configuration
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-change-this-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 days

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

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Create a new JWT access token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def decode_access_token(token: str) -> Optional[dict]:
    """Decode a JWT access token and return the payload"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None
