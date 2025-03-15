from fastapi import HTTPException, Depends, Cookie
import hashlib
from .database import get_db_connection

def hash_password(password: str) -> str:
    """Hash a password using SHA-256."""
    return hashlib.sha256(password.encode()).hexdigest()

def get_current_user(user_id: str = Cookie(None)):
    """Get the current user from the session cookie."""
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    try:
        cursor.execute('SELECT id FROM users WHERE id = %s', (user_id,))
        user = cursor.fetchone()
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        return user_id
    finally:
        cursor.close()
        conn.close() 