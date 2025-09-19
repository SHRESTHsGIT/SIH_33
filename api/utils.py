## api/utils.py

import pandas as pd
from datetime import datetime
import pytz
from pathlib import Path
from config import TIMEZONE, BRANCHES_DIR
from typing import Optional, Dict, Any

def get_current_time() -> datetime:
    """Get current time in configured timezone"""
    tz = pytz.timezone(TIMEZONE)
    return datetime.now(tz).replace(tzinfo=None)  # Remove timezone for CSV storage

def get_branch_files(branch_code: str) -> Dict[str, Path]:
    """Get file paths for a branch"""
    branch_dir = BRANCHES_DIR / branch_code
    return {
        'students': branch_dir / f'students_{branch_code}.csv',
        'attendance': branch_dir / f'attendance_{branch_code}.csv',
        'stats': branch_dir / f'stats_{branch_code}.csv',
        'sessions': branch_dir / f'sessions_{branch_code}.csv',
        'faces': branch_dir / 'faces',
        'qrcodes': branch_dir / 'qrcodes'
    }

def ensure_branch_structure(branch_code: str) -> None:
    """Ensure branch directory structure exists"""
    files = get_branch_files(branch_code)
    
    # Create directories
    for path in [files['faces'], files['qrcodes']]:
        path.mkdir(parents=True, exist_ok=True)
    
    # Create CSV files if they don't exist with proper headers
    if not files['students'].exists():
        files['students'].parent.mkdir(parents=True, exist_ok=True)
        df = pd.DataFrame(columns=['roll_no', 'name', 'face_path', 'qr_code_path', 'registered_on'])
        df.to_csv(files['students'], index=False)
    
    if not files['attendance'].exists():
        files['attendance'].parent.mkdir(parents=True, exist_ok=True)
        df = pd.DataFrame(columns=['session_id', 'roll_no', 'name', 'status', 'marked_at', 'method', 'marked_by'])
        df.to_csv(files['attendance'], index=False)
    
    if not files['stats'].exists():
        files['stats'].parent.mkdir(parents=True, exist_ok=True)
        df = pd.DataFrame(columns=['roll_no', 'name', 'present_days', 'absent_days', 'total_days', 'attendance_pct', 'last_present', 'last_absent'])
        df.to_csv(files['stats'], index=False)
    
    if not files['sessions'].exists():
        files['sessions'].parent.mkdir(parents=True, exist_ok=True)
        df = pd.DataFrame(columns=['session_id', 'teacher_id', 'branch_code', 'start_time', 'deadline_time', 'status'])
        df.to_csv(files['sessions'], index=False)

def validate_branch_exists(branch_code: str) -> bool:
    """Validate if branch exists"""
    try:
        from config import BRANCHES_CSV
        branches_df = pd.read_csv(BRANCHES_CSV)
        return branch_code in branches_df['branch_code'].values
    except Exception:
        return False

def generate_session_id(branch_code: str) -> str:
    """Generate unique session ID"""
    now = get_current_time()
    timestamp = now.strftime("%Y%m%d_%H%M%S")
    return f"S_{timestamp}_{branch_code}"

def is_session_active(session_id: str, branch_code: str) -> bool:
    """Check if session is active"""
    try:
        files = get_branch_files(branch_code)
        sessions_df = pd.read_csv(files['sessions'])
        
        session = sessions_df[sessions_df['session_id'] == session_id]
        if session.empty:
            return False
        
        session_data = session.iloc[0]
        if session_data['status'] != 'open':
            return False
        
        # Check if deadline passed
        deadline_time = pd.to_datetime(session_data['deadline_time'])
        current_time = get_current_time()
        
        return current_time < deadline_time
    except Exception:
        return False