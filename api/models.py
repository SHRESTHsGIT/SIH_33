from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from enum import Enum

class SessionStatus(str, Enum):
    OPEN = "open"
    CLOSED = "closed"
    EXPIRED = "expired"

class AttendanceMethod(str, Enum):
    FACE = "face"
    QR = "qr"
    MANUAL = "manual"
    AUTO = "auto"

class AttendanceStatus(str, Enum):
    PRESENT = "Present"
    ABSENT = "Absent"

# -------------------------
# Request Models
# -------------------------
class TeacherLogin(BaseModel):
    teacher_id: str = Field(..., min_length=1)
    password: str = Field(..., min_length=1)

class StudentRegister(BaseModel):
    roll_no: str = Field(..., pattern=r'^[A-Z]{2}\d{2}[A-Z]{3}\d{3}$')
    name: str = Field(..., min_length=1)
    branch_code: str = Field(..., min_length=1)
    face_image_path: Optional[str] = None
    qr_code_path: Optional[str] = None
    registered_on: Optional[datetime] = None

class StartSession(BaseModel):
    teacher_id: str = Field(..., min_length=1)
    branch_code: str = Field(..., min_length=1)
    deadline_minutes: int = Field(default=60, ge=5, le=480)  # 5 min to 8 hours

class MarkAttendance(BaseModel):
    session_id: str = Field(..., min_length=1)
    roll_no: Optional[str] = None
    method: AttendanceMethod
    qr_data: Optional[str] = None

class ManualOverride(BaseModel):
    session_id: str = Field(..., min_length=1)
    roll_no: str = Field(..., min_length=1)
    new_status: AttendanceStatus
    teacher_id: str = Field(..., min_length=1)
    reason: Optional[str] = None

# -------------------------
# Response Models
# -------------------------
class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    teacher_name: str
    expires_at: datetime

class SessionResponse(BaseModel):
    session_id: str
    branch_code: str
    start_time: datetime
    deadline_time: datetime
    status: SessionStatus

class AttendanceResponse(BaseModel):
    success: bool
    message: str
    already_marked: bool = False
    marked_at: Optional[datetime] = None
    method: Optional[AttendanceMethod] = None

class StudentInfo(BaseModel):
    roll_no: str
    name: str
    face_path: Optional[str] = None
    qr_code_path: Optional[str] = None
    registered_on: datetime

class AttendanceRecord(BaseModel):
    roll_no: str
    name: str
    status: AttendanceStatus
    marked_at: Optional[datetime] = None
    method: Optional[AttendanceMethod] = None
    marked_by: Optional[str] = None

class StatsRecord(BaseModel):
    roll_no: str
    name: str
    present_days: int = 0
    absent_days: int = 0
    total_days: int = 0
    attendance_pct: float = 0.0
    last_present: Optional[datetime] = None
    last_absent: Optional[datetime] = None
