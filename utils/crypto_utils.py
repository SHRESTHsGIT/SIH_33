## utils/crypto_utils.py

import bcrypt
import hmac
import hashlib
from config import SECRET_KEY

def hash_password(password: str) -> str:
    """Hash password using bcrypt"""
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')

def verify_password(password: str, hashed: str) -> bool:
    """Verify password against hash"""
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))

def generate_qr_signature(roll_no: str, branch_code: str = "") -> str:
    """Generate HMAC signature for QR code"""
    message = f"{roll_no}|{branch_code}"
    signature = hmac.new(
        SECRET_KEY.encode('utf-8'),
        message.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    return signature[:8]  # First 8 characters

def verify_qr_signature(roll_no: str, branch_code: str, signature: str) -> bool:
    """Verify QR code signature"""
    expected = generate_qr_signature(roll_no, branch_code)
    return hmac.compare_digest(expected, signature)