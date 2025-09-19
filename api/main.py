## api/main.py

from fastapi import FastAPI, HTTPException, Depends, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from datetime import timedelta
import pandas as pd
import numpy as np
from pathlib import Path
import shutil
from typing import List, Optional
import uuid

from .models import *
from .auth import authenticate_teacher, create_access_token, get_current_teacher
from .utils import *
from config import ACCESS_TOKEN_EXPIRE_MINUTES, BRANCHES_CSV
from services.face_service import FaceService
from services.qr_service import QRService
from services.session_service import SessionService
from services.data_service import DataService

app = FastAPI(title="Face Recognition Attendance System", version="1.0.0")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize services
face_service = FaceService()
qr_service = QRService()
session_service = SessionService()
data_service = DataService()

@app.on_event("startup")
async def startup_event():
    """Initialize application"""
    from config import setup_directories
    setup_directories()

# Authentication endpoints
@app.post("/api/teacher/login", response_model=LoginResponse)
async def login_teacher(login_data: TeacherLogin):
    """Authenticate teacher and return access token"""
    teacher = authenticate_teacher(login_data.teacher_id, login_data.password)
    if not teacher:
        raise HTTPException(
            status_code=401,
            detail="Incorrect teacher ID or password"
        )
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token, expires_at = create_access_token(
        data={"sub": teacher['teacher_id']},
        expires_delta=access_token_expires
    )
    
    return LoginResponse(
        access_token=access_token,
        teacher_name=teacher['teacher_name'],
        expires_at=expires_at
    )

# Branch endpoints
@app.get("/api/branches")
async def get_branches():
    """Get list of all branches"""
    try:
        df = pd.read_csv(BRANCHES_CSV)
        return df.to_dict('records')
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Session management endpoints
@app.post("/api/teacher/start_session", response_model=SessionResponse)
async def start_attendance_session(
    session_data: StartSession,
    current_teacher: dict = Depends(get_current_teacher)
):
    """Start a new attendance session"""
    if not validate_branch_exists(session_data.branch_code):
        raise HTTPException(status_code=404, detail="Branch not found")
    
    # Check if there's already an active session
    active_session = session_service.get_active_session(session_data.branch_code)
    if active_session:
        raise HTTPException(
            status_code=400,
            detail="There's already an active session for this branch"
        )
    
    try:
        session = session_service.start_session(
            teacher_id=current_teacher['teacher_id'],
            branch_code=session_data.branch_code,
            deadline_minutes=session_data.deadline_minutes
        )
        return session
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/teacher/close_session")
async def close_attendance_session(
    session_id: str,
    branch_code: str,
    current_teacher: dict = Depends(get_current_teacher)
):
    """Manually close attendance session"""
    try:
        success = session_service.close_session(session_id, branch_code, current_teacher['teacher_id'])
        if not success:
            raise HTTPException(status_code=404, detail="Session not found or already closed")
        return {"message": "Session closed successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/session/{branch_code}/active")
async def get_active_session(branch_code: str):
    """Get active session for a branch"""
    if not validate_branch_exists(branch_code):
        raise HTTPException(status_code=404, detail="Branch not found")
    
    session = session_service.get_active_session(branch_code)
    if not session:
        return {"active": False}
    
    return {"active": True, "session": session}

# Student registration endpoints
@app.post("/api/students/register")
async def register_student(
    roll_no: str = Form(...),
    name: str = Form(...),
    branch_code: str = Form(...),
    face_image: UploadFile = File(...)
):
    """Register a new student with face image"""
    if not validate_branch_exists(branch_code):
        raise HTTPException(status_code=404, detail="Branch not found")
    
    ensure_branch_structure(branch_code)
    
    try:
        # Check if student already exists
        files = get_branch_files(branch_code)
        students_df = pd.read_csv(files['students'])
        
        if roll_no in students_df['roll_no'].values:
            raise HTTPException(status_code=400, detail="Student already registered")
        
        # Save face image
        face_filename = f"{roll_no}_{name.replace(' ', '_')}.jpg"
        face_path = files['faces'] / face_filename
        
        # Read and save image
        image_data = await face_image.read()
        with open(face_path, 'wb') as f:
            f.write(image_data)
        
        # Generate QR code
        qr_filename = f"{roll_no}.png"
        qr_path = files['qrcodes'] / qr_filename
        qr_service.generate_qr_code(roll_no, branch_code, str(qr_path))
        
        # Add to students CSV
        student_data = {
            'roll_no': roll_no,
            'name': name,
            'face_path': str(face_path),
            'qr_code_path': str(qr_path),
            'registered_on': get_current_time()
        }
        
        new_row = pd.DataFrame([student_data])
        students_df = pd.concat([students_df, new_row], ignore_index=True)
        students_df.to_csv(files['students'], index=False)
        
        # Initialize face embeddings
        face_service.update_embeddings(branch_code)
        
        return {"message": "Student registered successfully", "qr_code_path": str(qr_path)}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/students/{branch_code}", response_model=List[StudentInfo])
async def get_students(branch_code: str):
    """Get list of students for a branch"""
    if not validate_branch_exists(branch_code):
        raise HTTPException(status_code=404, detail="Branch not found")
    
    try:
        files = get_branch_files(branch_code)
        if not files['students'].exists():
            return []
        
        students_df = pd.read_csv(files['students'])
        students_df['registered_on'] = pd.to_datetime(students_df['registered_on'])
        
        return [StudentInfo(**row) for _, row in students_df.iterrows()]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Attendance marking endpoints
@app.post("/api/attendance/mark", response_model=AttendanceResponse)
async def mark_attendance(
    session_id: str = Form(...),
    method: str = Form(...),
    roll_no: Optional[str] = Form(None),
    qr_data: Optional[str] = Form(None),
    face_image: Optional[UploadFile] = File(None)
):
    """Mark attendance via face recognition or QR code"""
    # Validate method
    if method not in ['face', 'qr']:
        raise HTTPException(status_code=400, detail="Invalid method")
    
    # Get session details
    session = session_service.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    if not is_session_active(session_id, session['branch_code']):
        raise HTTPException(status_code=400, detail="Session is not active or has expired")
    
    try:
        branch_code = session['branch_code']
        
        # Check if already marked
        if data_service.is_already_marked(session_id, roll_no or "", branch_code):
            attendance_record = data_service.get_attendance_record(session_id, roll_no or "", branch_code)
            return AttendanceResponse(
                success=False,
                message="Already marked",
                already_marked=True,
                marked_at=attendance_record.get('marked_at'),
                method=attendance_record.get('method')
            )
        
        if method == 'face' and face_image:
            # Face recognition
            image_data = await face_image.read()
            result = face_service.recognize_face(image_data, branch_code)
            
            if result['success']:
                roll_no = result['roll_no']
                # Mark attendance
                data_service.mark_attendance(
                    session_id=session_id,
                    roll_no=roll_no,
                    branch_code=branch_code,
                    method='face',
                    marked_by='student'
                )
                return AttendanceResponse(
                    success=True,
                    message=f"Attendance marked for {roll_no}",
                    marked_at=get_current_time(),
                    method='face'
                )
            else:
                return AttendanceResponse(
                    success=False,
                    message="Face not recognized"
                )
        
        elif method == 'qr' and qr_data:
            # QR code recognition
            result = qr_service.decode_qr_data(qr_data, branch_code)
            
            if result['success']:
                roll_no = result['roll_no']
                # Mark attendance
                data_service.mark_attendance(
                    session_id=session_id,
                    roll_no=roll_no,
                    branch_code=branch_code,
                    method='qr',
                    marked_by='student'
                )
                return AttendanceResponse(
                    success=True,
                    message=f"Attendance marked for {roll_no}",
                    marked_at=get_current_time(),
                    method='qr'
                )
            else:
                return AttendanceResponse(
                    success=False,
                    message="Invalid QR code"
                )
        
        else:
            raise HTTPException(status_code=400, detail="Invalid request data")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Manual override endpoints
@app.post("/api/teacher/manual_override")
async def manual_override(
    override_data: ManualOverride,
    current_teacher: dict = Depends(get_current_teacher)
):
    """Manually override attendance status"""
    # Get session details
    session = session_service.get_session(override_data.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    try:
        success = data_service.manual_override_attendance(
            session_id=override_data.session_id,
            roll_no=override_data.roll_no,
            branch_code=session['branch_code'],
            new_status=override_data.new_status.value,
            teacher_id=current_teacher['teacher_id'],
            reason=override_data.reason
        )
        
        if success:
            return {"message": "Attendance updated successfully"}
        else:
            raise HTTPException(status_code=404, detail="Student not found in this session")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Attendance data endpoints
@app.get("/api/attendance/{branch_code}/session/{session_id}", response_model=List[AttendanceRecord])
async def get_session_attendance(
    branch_code: str,
    session_id: str,
    current_teacher: dict = Depends(get_current_teacher)
):
    """Get attendance records for a specific session"""
    if not validate_branch_exists(branch_code):
        raise HTTPException(status_code=404, detail="Branch not found")
    
    try:
        records = data_service.get_session_attendance(session_id, branch_code)
        return [AttendanceRecord(**record) for record in records]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/stats/{branch_code}", response_model=List[StatsRecord])
async def get_branch_stats(branch_code: str):
    """Get attendance statistics for a branch"""
    if not validate_branch_exists(branch_code):
        raise HTTPException(status_code=404, detail="Branch not found")
    
    try:
        stats = data_service.get_attendance_stats(branch_code)
        return [StatsRecord(**stat) for stat in stats]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# File download endpoints
@app.get("/api/download/qr/{branch_code}/{roll_no}")
async def download_qr_code(branch_code: str, roll_no: str):
    """Download QR code for a student"""
    if not validate_branch_exists(branch_code):
        raise HTTPException(status_code=404, detail="Branch not found")
    
    files = get_branch_files(branch_code)
    qr_path = files['qrcodes'] / f"{roll_no}.png"
    
    if not qr_path.exists():
        raise HTTPException(status_code=404, detail="QR code not found")
    
    return FileResponse(qr_path, filename=f"{roll_no}_qr.png")

@app.get("/api/export/attendance/{branch_code}")
async def export_attendance_csv(
    branch_code: str,
    session_id: Optional[str] = None,
    current_teacher: dict = Depends(get_current_teacher)
):
    """Export attendance data as CSV"""
    if not validate_branch_exists(branch_code):
        raise HTTPException(status_code=404, detail="Branch not found")
    
    try:
        files = get_branch_files(branch_code)
        attendance_df = pd.read_csv(files['attendance'])
        
        if session_id:
            attendance_df = attendance_df[attendance_df['session_id'] == session_id]
            filename = f"attendance_{branch_code}_{session_id}.csv"
        else:
            filename = f"attendance_{branch_code}_all.csv"
        
        # Create temporary file
        temp_path = files['attendance'].parent / filename
        attendance_df.to_csv(temp_path, index=False)
        
        return FileResponse(temp_path, filename=filename)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/export/stats/{branch_code}")
async def export_stats_csv(
    branch_code: str,
    current_teacher: dict = Depends(get_current_teacher)
):
    """Export statistics as CSV"""
    if not validate_branch_exists(branch_code):
        raise HTTPException(status_code=404, detail="Branch not found")
    
    try:
        files = get_branch_files(branch_code)
        if not files['stats'].exists():
            # Generate stats if not exists
            data_service.update_stats(branch_code)
        
        filename = f"stats_{branch_code}.csv"
        return FileResponse(files['stats'], filename=filename)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
