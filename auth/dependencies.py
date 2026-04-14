from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from typing import Optional
from auth.security import decode_access_token
from config.database import SessionLocal
from database.models import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)

def get_current_user(token: str = Depends(oauth2_scheme)):
    """Dependency to get the current authenticated user from JWT via Database."""
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    payload = decode_access_token(token)
    if payload is None:
        raise credentials_exception
        
    user_id_val = payload.get("sub")
    if user_id_val is None:
        raise credentials_exception
        
    db = SessionLocal()
    try:
        # User ID might be string username from old sessions or integer ID from new ones
        if isinstance(user_id_val, str) and not user_id_val.isdigit():
            # Try to look up by email/username if it's an old token
            user = db.query(User).filter(User.email == user_id_val).first()
        else:
            user = db.query(User).filter(User.id == int(user_id_val)).first()
            
        if user is None or not user.is_active:
            raise credentials_exception
        return user
    finally:
        db.close()

def get_current_admin(current_user: User = Depends(get_current_user)):
    """Dependency to enforce admin role."""
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="The user does not have enough privileges"
        )
    return current_user

def get_optional_current_user(token: Optional[str] = Depends(oauth2_scheme)):
    """Optional version of the current user dependency."""
    if not token:
        return None
    try:
        return get_current_user(token)
    except HTTPException:
        return None
