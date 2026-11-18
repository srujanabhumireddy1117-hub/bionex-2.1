import base64
import hashlib
import hmac
import json
import time
from datetime import datetime
from typing import Optional, Dict, Any

from fastapi import Depends, HTTPException, Header, status
from pydantic import BaseModel, EmailStr, Field

from backend.database import get_connection, hash_password

SECRET_KEY = "bionex_hospital_autonomous_secret_key_2026_super_secure"


def create_token(payload: dict) -> str:
    """Create a tamper-proof HMAC-SHA256 signed token."""
    header = {"alg": "HS256", "typ": "JWT"}
    header_b64 = base64.urlsafe_b64encode(json.dumps(header).encode()).decode().rstrip("=")
    
    payload_data = payload.copy()
    payload_data["exp"] = int(time.time()) + 86400 * 7  # 7 days validity
    payload_b64 = base64.urlsafe_b64encode(json.dumps(payload_data).encode()).decode().rstrip("=")
    
    signing_input = f"{header_b64}.{payload_b64}".encode()
    signature = hmac.new(SECRET_KEY.encode(), signing_input, hashlib.sha256).digest()
    sig_b64 = base64.urlsafe_b64encode(signature).decode().rstrip("=")
    
    return f"{header_b64}.{payload_b64}.{sig_b64}"


def decode_token(token: str) -> Optional[dict]:
    """Verify and decode HMAC-SHA256 token."""
    try:
        parts = token.split(".")
        if len(parts) != 3:
            return None
        header_b64, payload_b64, sig_b64 = parts
        
        signing_input = f"{header_b64}.{payload_b64}".encode()
        expected_sig = hmac.new(SECRET_KEY.encode(), signing_input, hashlib.sha256).digest()
        actual_sig = base64.urlsafe_b64decode(sig_b64 + "=" * (-len(sig_b64) % 4))
        
        if not hmac.compare_digest(expected_sig, actual_sig):
            return None
        
        payload_json = base64.urlsafe_b64decode(payload_b64 + "=" * (-len(payload_b64) % 4)).decode()
        payload = json.loads(payload_json)
        
        if payload.get("exp", 0) < int(time.time()):
            return None
        
        return payload
    except Exception:
        return None


class LoginRequest(BaseModel):
    email: str
    password: str
    role_hint: Optional[str] = None  # 'Admin' or 'User'


class RegisterRequest(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    email: str = Field(min_length=5, max_length=120)
    password: str = Field(min_length=6, max_length=60)
    department: str = Field(min_length=2, max_length=100)
    role: str = Field(default="User", pattern="^(User|Admin)$")


class ForgotPasswordRequest(BaseModel):
    email: str
    new_password: Optional[str] = None


def authenticate_user(email: str, password: str) -> Optional[Dict[str, Any]]:
    with get_connection() as conn:
        user = conn.execute(
            "SELECT * FROM users WHERE LOWER(email) = LOWER(?) AND is_active = 1",
            (email.strip(),)
        ).fetchone()
        
        if not user:
            return None
            
        p_hash = hash_password(password)
        if user["password_hash"] == p_hash:
            return dict(user)
    return None


def get_current_user(authorization: Optional[str] = Header(None)) -> Dict[str, Any]:
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Authorization header"
        )
    
    token = authorization.replace("Bearer ", "").strip()
    payload = decode_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
        )
    
    with get_connection() as conn:
        user = conn.execute(
            "SELECT id, email, name, role, department, is_active FROM users WHERE id = ?",
            (payload.get("user_id"),)
        ).fetchone()
        
        if not user or not user["is_active"]:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User account inactive or not found"
            )
            
        return dict(user)


def require_admin(current_user: dict = Depends(get_current_user)) -> dict:
    if current_user.get("role") != "Admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrative privileges required"
        )
    return current_user
