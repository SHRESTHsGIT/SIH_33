## services/data_service.py

import pandas as pd
from datetime import datetime
from typing import Dict, Any, List, Optional
from pathlib import Path
import numpy as np
from api.utils import get_branch_files, get_current_time, ensure_branch_structure

class DataService:
    def __init__(self):
        pass
    
    def mark_attendance(
        self,
        session_id: str,
        roll_no: str,
        branch_code: str,
        method: str,
        marked_by: str = "student"
    ) -> bool:
        """Mark attendance for a student"""
        try:
            ensure_branch_structure(branch_code)
            files = get_branch_files(branch_code)
            
            # Get student name
            students_df = pd.read_csv(files['students'])
            student = students_df[students_df['roll_no'] == roll_no]
            
            if student.empty:
                return False
            
            student_name = student.iloc[0]['name']
            
            # Add attendance record
            attendance_record = {
                'session_id': session_id,
                'roll_no': roll_no,
                'name': student_name,
                'status': 'Present',
                'marked_at': get_current_time(),
                'method': method,
                'marked_by': marked_by
            }
            
            # Append to attendance CSV
            attendance_df = pd.read_csv(files['attendance'])
            new_record = pd.DataFrame([attendance_record])
            attendance_df = pd.concat([attendance_df, new_record], ignore_index=True)
            attendance_df.to_csv(files['attendance'], index=False)
            
            # Update stats
            self.update_stats(branch_code)
            
            return True
        except Exception as e:
            print(f"Error marking attendance: {e}")
            return False
    
    def is_already_marked(self, session_id: str, roll_no: str, branch_code: str) -> bool:
        """Check if student already marked attendance for this session"""
        try:
            files = get_branch_files(branch_code)
            if not files['attendance'].exists():
                return False
            
            attendance_df = pd.read_csv(files['attendance'])
            existing = attendance_df[
                (attendance_df['session_id'] == session_id) & 
                (attendance_df['roll_no'] == roll_no)
            ]
            
            return not existing.empty
        except Exception:
            return False
    
    def get_attendance_record(self, session_id: str, roll_no: str, branch_code: str) -> Dict[str, Any]:
        """Get attendance record for a student in a session"""
        try:
            files = get_branch_files(branch_code)
            attendance_df = pd.read_csv(files['attendance'])
            
            record = attendance_df[
                (attendance_df['session_id'] == session_id) & 
                (attendance_df['roll_no'] == roll_no)
            ]
            
            if not record.empty:
                return record.iloc[0].to_dict()
            return {}
        except Exception:
            return {}
    
    def manual_override_attendance(
        self,
        session_id: str,
        roll_no: str,
        branch_code: str,
        new_status: str,
        teacher_id: str,
        reason: Optional[str] = None
    ) -> bool:
        """Manually override attendance status"""
        try:
            files = get_branch_files(branch_code)
            
            # Get student name
            students_df = pd.read_csv(files['students'])
            student = students_df[students_df['roll_no'] == roll_no]
            
            if student.empty:
                return False
            
            student_name = student.iloc[0]['name']
            
            # Check if record exists
            attendance_df = pd.read_csv(files['attendance'])
            existing_mask = (
                (attendance_df['session_id'] == session_id) & 
                (attendance_df['roll_no'] == roll_no)
            )
            
            if existing_mask.any():
                # Update existing record
                attendance_df.loc[existing_mask, 'status'] = new_status
                attendance_df.loc[existing_mask, 'marked_at'] = get_current_time()
                attendance_df.loc[existing_mask, 'method'] = 'manual'
                attendance_df.loc[existing_mask, 'marked_by'] = teacher_id
            else:
                # Create new record
                new_record = {
                    'session_id': session_id,
                    'roll_no': roll_no,
                    'name': student_name,
                    'status': new_status,
                    'marked_at': get_current_time(),
                    'method': 'manual',
                    'marked_by': teacher_id
                }
                new_row = pd.DataFrame([new_record])
                attendance_df = pd.concat([attendance_df, new_row], ignore_index=True)
            
            attendance_df.to_csv(files['attendance'], index=False)
            
            # Update stats
            self.update_stats(branch_code)
            
            return True
        except Exception as e:
            print(f"Error in manual override: {e}")
            return False
    
    def get_session_attendance(self, session_id: str, branch_code: str) -> List[Dict[str, Any]]:
        """Get all attendance records for a session"""
        try:
            files = get_branch_files(branch_code)
            
            # Get all students for the branch
            students_df = pd.read_csv(files['students'])
            
            # Get attendance records for this session
            attendance_df = pd.read_csv(files['attendance'])
            session_attendance = attendance_df[attendance_df['session_id'] == session_id]
            
            # Create complete list with all students
            result = []
            for _, student in students_df.iterrows():
                roll_no = student['roll_no']
                name = student['name']
                
                # Find attendance record
                student_attendance = session_attendance[session_attendance['roll_no'] == roll_no]
                
                if not student_attendance.empty:
                    record = student_attendance.iloc[0]
                    result.append({
                        'roll_no': roll_no,
                        'name': name,
                        'status': record['status'],
                        'marked_at': pd.to_datetime(record['marked_at']) if pd.notna(record['marked_at']) else None,
                        'method': record.get('method'),
                        'marked_by': record.get('marked_by')
                    })
                else:
                    result.append({
                        'roll_no': roll_no,
                        'name': name,
                        'status': 'Absent',
                        'marked_at': None,
                        'method': None,
                        'marked_by': None
                    })
            
            return result
        except Exception as e:
            print(f"Error getting session attendance: {e}")
            return []
    
    def get_attendance_stats(self, branch_code: str) -> List[Dict[str, Any]]:
        """Get attendance statistics for a branch"""
        try:
            files = get_branch_files(branch_code)
            
            if not files['stats'].exists():
                self.update_stats(branch_code)
            
            stats_df = pd.read_csv(files['stats'])
            
            # Convert datetime columns
            for col in ['last_present', 'last_absent']:
                if col in stats_df.columns:
                    stats_df[col] = pd.to_datetime(stats_df[col], errors='coerce')
            
            return stats_df.to_dict('records')
        except Exception as e:
            print(f"Error getting stats: {e}")
            return []
    
    def update_stats(self, branch_code: str) -> None:
        """Update attendance statistics"""
        try:
            files = get_branch_files(branch_code)
            
            students_df = pd.read_csv(files['students'])
            attendance_df = pd.read_csv(files['attendance'])
            
            if attendance_df.empty:
                # Create empty stats file
                stats_data = []
                for _, student in students_df.iterrows():
                    stats_data.append({
                        'roll_no': student['roll_no'],
                        'name': student['name'],
                        'present_days': 0,
                        'absent_days': 0,
                        'total_days': 0,
                        'attendance_pct': 0.0,
                        'last_present': None,
                        'last_absent': None
                    })
                
                stats_df = pd.DataFrame(stats_data)
                stats_df.to_csv(files['stats'], index=False)
                return
            
            # Calculate stats for each student
            stats_data = []
            
            # Get unique sessions (total days)
            total_sessions = attendance_df['session_id'].nunique()
            
            for _, student in students_df.iterrows():
                roll_no = student['roll_no']
                name = student['name']
                
                # Get student's attendance records
                student_records = attendance_df[attendance_df['roll_no'] == roll_no]
                
                # Count present and absent
                present_count = len(student_records[student_records['status'] == 'Present'])
                absent_count = len(student_records[student_records['status'] == 'Absent'])
                
                # For students with no records, assume absent for all sessions
                if student_records.empty:
                    absent_count = total_sessions
                    present_count = 0
                else:
                    # Add absent count for sessions not attended
                    attended_sessions = student_records['session_id'].nunique()
                    absent_count += (total_sessions - attended_sessions)
                
                total_days = total_sessions
                attendance_pct = (present_count / total_days * 100) if total_days > 0 else 0.0
                
                # Get last present and absent dates
                present_records = student_records[student_records['status'] == 'Present']
                absent_records = student_records[student_records['status'] == 'Absent']
                
                last_present = None
                last_absent = None
                
                if not present_records.empty:
                    last_present = pd.to_datetime(present_records['marked_at']).max()
                
                if not absent_records.empty:
                    last_absent = pd.to_datetime(absent_records['marked_at']).max()
                
                stats_data.append({
                    'roll_no': roll_no,
                    'name': name,
                    'present_days': present_count,
                    'absent_days': absent_count,
                    'total_days': total_days,
                    'attendance_pct': round(attendance_pct, 2),
                    'last_present': last_present,
                    'last_absent': last_absent
                })
            
            stats_df = pd.DataFrame(stats_data)
            stats_df.to_csv(files['stats'], index=False)
            
        except Exception as e:
            print(f"Error updating stats: {e}")
    
    def mark_absentees_auto(self, session_id: str, branch_code: str) -> None:
        """Automatically mark absent students when session expires"""
        try:
            files = get_branch_files(branch_code)
            
            # Get all students
            students_df = pd.read_csv(files['students'])
            
            # Get current attendance for this session
            attendance_df = pd.read_csv(files['attendance'])
            session_attendance = attendance_df[attendance_df['session_id'] == session_id]
            
            # Find students not marked
            marked_students = set(session_attendance['roll_no'].values)
            all_students = set(students_df['roll_no'].values)
            absent_students = all_students - marked_students
            
            # Mark absent students
            for roll_no in absent_students:
                student = students_df[students_df['roll_no'] == roll_no].iloc[0]
                
                absent_record = {
                    'session_id': session_id,
                    'roll_no': roll_no,
                    'name': student['name'],
                    'status': 'Absent',
                    'marked_at': get_current_time(),
                    'method': 'auto',
                    'marked_by': 'system'
                }
                
                new_row = pd.DataFrame([absent_record])
                attendance_df = pd.concat([attendance_df, new_row], ignore_index=True)
            
            attendance_df.to_csv(files['attendance'], index=False)
            
            # Update stats
            self.update_stats(branch_code)
            
        except Exception as e:
            print(f"Error marking absentees: {e}")
