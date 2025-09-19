# services/session_service.py
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from api.utils import (
    get_branch_files, 
    get_current_time, 
    ensure_branch_structure, 
    generate_session_id
)
from services.data_service import DataService

class SessionService:
    def __init__(self):
        self.data_service = DataService()
    
    def start_session(
        self, 
        teacher_id: str, 
        branch_code: str, 
        deadline_minutes: int = 60
    ) -> Dict[str, Any]:
        """Start a new attendance session"""
        try:
            ensure_branch_structure(branch_code)
            files = get_branch_files(branch_code)
            
            # Generate session ID
            session_id = generate_session_id(branch_code)
            
            # Calculate times
            start_time = get_current_time()
            deadline_time = start_time + timedelta(minutes=deadline_minutes)
            
            # Create session record
            session_data = {
                'session_id': session_id,
                'teacher_id': teacher_id,
                'branch_code': branch_code,
                'start_time': start_time,
                'deadline_time': deadline_time,
                'status': 'open'
            }
            
            # Add to sessions CSV
            sessions_df = pd.read_csv(files['sessions'])
            new_session = pd.DataFrame([session_data])
            sessions_df = pd.concat([sessions_df, new_session], ignore_index=True)
            sessions_df.to_csv(files['sessions'], index=False)
            
            return {
                'session_id': session_id,
                'branch_code': branch_code,
                'start_time': start_time,
                'deadline_time': deadline_time,
                'status': 'open'
            }
            
        except Exception as e:
            print(f"Error starting session: {e}")
            raise e
    
    def close_session(self, session_id: str, branch_code: str, teacher_id: str) -> bool:
        """Close an attendance session"""
        try:
            files = get_branch_files(branch_code)
            sessions_df = pd.read_csv(files['sessions'])
            
            # Find session
            session_mask = sessions_df['session_id'] == session_id
            
            if not session_mask.any():
                return False
            
            # Update session status
            sessions_df.loc[session_mask, 'status'] = 'closed'
            sessions_df.to_csv(files['sessions'], index=False)
            
            # Mark absent students automatically
            self.data_service.mark_absentees_auto(session_id, branch_code)
            
            return True
            
        except Exception as e:
            print(f"Error closing session: {e}")
            return False
    
    def get_active_session(self, branch_code: str) -> Optional[Dict[str, Any]]:
        """Get active session for a branch"""
        try:
            files = get_branch_files(branch_code)
            if not files['sessions'].exists():
                return None
            
            sessions_df = pd.read_csv(files['sessions'])
            
            # Find open sessions
            open_sessions = sessions_df[sessions_df['status'] == 'open']
            
            if open_sessions.empty:
                return None
            
            # Check if any session is still within deadline
            current_time = get_current_time()
            
            for _, session in open_sessions.iterrows():
                deadline_time = pd.to_datetime(session['deadline_time'])
                
                if current_time < deadline_time:
                    return {
                        'session_id': session['session_id'],
                        'teacher_id': session['teacher_id'],
                        'branch_code': session['branch_code'],
                        'start_time': pd.to_datetime(session['start_time']),
                        'deadline_time': deadline_time,
                        'status': session['status']
                    }
                else:
                    # Auto-close expired session
                    self.close_session(session['session_id'], branch_code, session['teacher_id'])
            
            return None
            
        except Exception as e:
            print(f"Error getting active session: {e}")
            return None
    
    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session details by ID"""
        try:
            # We need to search across all branches since session_id should be unique
            from config import BRANCHES_CSV
            branches_df = pd.read_csv(BRANCHES_CSV)
            
            for _, branch in branches_df.iterrows():
                branch_code = branch['branch_code']
                files = get_branch_files(branch_code)
                
                if files['sessions'].exists():
                    sessions_df = pd.read_csv(files['sessions'])
                    session = sessions_df[sessions_df['session_id'] == session_id]
                    
                    if not session.empty():
                        session_data = session.iloc[0]
                        return {
                            'session_id': session_data['session_id'],
                            'teacher_id': session_data['teacher_id'],
                            'branch_code': session_data['branch_code'],
                            'start_time': pd.to_datetime(session_data['start_time']),
                            'deadline_time': pd.to_datetime(session_data['deadline_time']),
                            'status': session_data['status']
                        }
            
            return None
            
        except Exception as e:
            print(f"Error getting session: {e}")
            return None
    
    def get_session_time_remaining(self, session_id: str, branch_code: str) -> Optional[int]:
        """Get remaining time in minutes for a session"""
        try:
            files = get_branch_files(branch_code)
            sessions_df = pd.read_csv(files['sessions'])
            
            session = sessions_df[sessions_df['session_id'] == session_id]
            
            if session.empty:
                return None
            
            session_data = session.iloc[0]
            
            if session_data['status'] != 'open':
                return 0
            
            deadline_time = pd.to_datetime(session_data['deadline_time'])
            current_time = get_current_time()
            
            if current_time >= deadline_time:
                return 0
            
            time_remaining = deadline_time - current_time
            return int(time_remaining.total_seconds() / 60)
            
        except Exception as e:
            print(f"Error getting session time remaining: {e}")
            return None
    
    def cleanup_expired_sessions(self) -> None:
        """Clean up expired sessions across all branches"""
        try:
            from config import BRANCHES_CSV
            branches_df = pd.read_csv(BRANCHES_CSV)
            
            current_time = get_current_time()
            
            for _, branch in branches_df.iterrows():
                branch_code = branch['branch_code']
                files = get_branch_files(branch_code)
                
                if files['sessions'].exists():
                    sessions_df = pd.read_csv(files['sessions'])
                    
                    # Find expired open sessions
                    expired_sessions = sessions_df[
                        (sessions_df['status'] == 'open') &
                        (pd.to_datetime(sessions_df['deadline_time']) < current_time)
                    ]
                    
                    for _, session in expired_sessions.iterrows():
                        print(f"Auto-closing expired session: {session['session_id']}")
                        self.close_session(
                            session['session_id'], 
                            branch_code, 
                            session['teacher_id']
                        )
                        
        except Exception as e:
            print(f"Error cleaning up expired sessions: {e}")
