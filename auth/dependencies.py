from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from typing import Optional
from auth.security import decode_access_token
from auth.user_manager import UserManager
from auth.session_manager import SessionManager

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

def get_current_user(token: str = Depends(oauth2_scheme)):
    """Dependency to get the current authenticated user from JWT."""
    print(f"DEBUG AUTH: Received token length: {len(token) if token else 'None'}")
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    # Check if token is in active sessions (if tracking)
    sm = SessionManager()
    if not sm.is_token_valid(token):
        print("DEBUG AUTH: Token not found in active sessions")
        raise credentials_exception
        
    payload = decode_access_token(token)
    if payload is None:
        print("DEBUG AUTH: decode_access_token failed")
        raise credentials_exception
        
    username: str = payload.get("sub")
    if username is None:
        print("DEBUG AUTH: username missing from payload")
        raise credentials_exception
        
    um = UserManager()
    user = um.get_user_by_username(username)
    if user is None:
        print("DEBUG AUTH: User not found in database")
        raise credentials_exception
        
    print("DEBUG AUTH: Successfully authenticated user:", username)
    return user

def get_optional_current_user(token: Optional[str] = Depends(oauth2_scheme)):
    """Optional version of the current user dependency."""
    if not token:
        return None
    try:
        return get_current_user(token)
    except HTTPException:
        return None
