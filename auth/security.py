import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Optional, Dict
from authlib.jose import jwt
from config.auth_settings import JWT_SECRET_KEY, JWT_ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES

from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_password_hash(password: str) -> str:
    """Hash a password using bcrypt."""
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against a stored bcrypt hash."""
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a new JWT access token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": int(expire.timestamp())})
    header = {"alg": JWT_ALGORITHM}
    payload = to_encode
    
    token = jwt.encode(header, payload, JWT_SECRET_KEY)
    return token.decode('utf-8')

def decode_access_token(token: str) -> Optional[Dict]:
    """Decode and verify a JWT access token."""
    try:
        claims = jwt.decode(token, JWT_SECRET_KEY)
        claims.validate()
        return claims
    except Exception:
        return None
