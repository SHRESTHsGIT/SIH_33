## api/auth.py

from datetime import datetime, timedelta
from typing import Optional
import jwt
from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import pandas as pd
from config import SECRET_KEY, ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES, TEACHERS_CSV
from utils.crypto_utils import verify_password

security = HTTPBearer()

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Create JWT access token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt, expire

def authenticate_teacher(teacher_id: str, password: str) -> Optional[dict]:
    """Authenticate teacher credentials"""
    try:
        teachers_df = pd.read_csv(TEACHERS_CSV)
        teacher = teachers_df[teachers_df['teacher_id'] == teacher_id]
        
        if teacher.empty:
            return None
        
        teacher_data = teacher.iloc[0]
        if verify_password(password, teacher_data['password']):
            return {
                'teacher_id': teacher_data['teacher_id'],
                'teacher_name': teacher_data['teacher_name']
            }
        return None
    except Exception:
        return None

def get_current_teacher(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Get current authenticated teacher from JWT token"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        teacher_id: str = payload.get("sub")
        if teacher_id is None:
            raise credentials_exception
    except jwt.PyJWTError:
        raise credentials_exception
    
    # Verify teacher still exists
    try:
        teachers_df = pd.read_csv(TEACHERS_CSV)
        teacher = teachers_df[teachers_df['teacher_id'] == teacher_id]
        if teacher.empty:
            raise credentials_exception
        
        teacher_data = teacher.iloc[0]
        return {
            'teacher_id': teacher_data['teacher_id'],
            'teacher_name': teacher_data['teacher_name']
        }
    except Exception:
        raise credentials_exception