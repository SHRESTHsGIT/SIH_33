## ui/pages/branch_dashboard.py

import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta

def show_dashboard(branch_code, api_base):
    """Show branch dashboard"""
    
    st.title(f"🏠 Dashboard - {branch_code}")
    
    # Get active session
    try:
        response = requests.get(f"{api_base}/session/{branch_code}/active")
        session_data = response.json() if response.status_code == 200 else {"active": False}
    except Exception as e:
        st.error(f"Error fetching session data: {e}")
        session_data = {"active": False}
    
    # Status cards
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if session_data["active"]:
            st.markdown("""
            <div class="status-card success-card">
                <h4>✅ Session Status</h4>
                <p><strong>ACTIVE</strong></p>
                <p>Students can mark attendance</p>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown("""
            <div class="status-card error-card">
                <h4>❌ Session Status</h4>
                <p><strong>INACTIVE</strong></p>
                <p>No active attendance session</p>
            </div>
            """, unsafe_allow_html=True)
    
    with col2:
        try:
            response = requests.get(f"{api_base}/students/{branch_code}")
            students_count = len(response.json()) if response.status_code == 200 else 0
        except:
            students_count = 0
        
        st.markdown(f"""
        <div class="status-card">
            <h4>👥 Total Students</h4>
            <p><strong>{students_count}</strong></p>
            <p>Registered students</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown(f"""
        <div class="status-card">
            <h4>📅 Current Date</h4>
            <p><strong>{datetime.now().strftime('%Y-%m-%d')}</strong></p>
            <p>{datetime.now().strftime('%A')}</p>
        </div>
        """, unsafe_allow_html=True)
    
    # Active session details
    if session_data["active"]:
        st.subheader("📋 Active Session Details")
        session = session_data["session"]
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.info(f"**Session ID:** {session['session_id']}")
            st.info(f"**Started:** {session['start_time']}")
        
        with col2:
            deadline = datetime.fromisoformat(session['deadline_time'].replace('Z', '+00:00'))
            now = datetime.now()
            
            if now < deadline:
                remaining = deadline - now
                minutes = int(remaining.total_seconds() / 60)
                st.info(f"**⏰ Time Remaining:** {minutes} minutes")
            else:
                st.error("⏰ **Session Expired!**")
        
        # Close session button
        if st.button("🛑 Close Session", type="secondary", use_container_width=True):
            try:
                response = requests.post(
                    f"{api_base}/teacher/close_session",
                    params={
                        "session_id": session['session_id'],
                        "branch_code": branch_code
                    },
                    headers=headers
                )
                
                if response.status_code == 200:
                    st.success("✅ Session closed successfully!")
                    st.rerun()
                else:
                    st.error("❌ Failed to close session.")
            except Exception as e:
                st.error(f"❌ Error closing session: {e}")
    
    # Current attendance section
    if session_data["active"]:
        st.subheader("📋 Current Session Attendance")
        
        try:
            response = requests.get(
                f"{api_base}/attendance/{branch_code}/session/{session_data['session']['session_id']}", 
                headers=headers
            )
            
            if response.status_code == 200:
                attendance = response.json()
                
                if attendance:
                    df = pd.DataFrame(attendance)
                    
                    # Summary statistics
                    total_students = len(df)
                    present_count = len(df[df['status'] == 'Present'])
                    absent_count = total_students - present_count
                    
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        st.metric("👥 Total Students", total_students)
                    with col2:
                        st.metric("✅ Present", present_count)
                    with col3:
                        st.metric("❌ Absent", absent_count)
                    
                    # Attendance table
                    st.dataframe(
                        df[['roll_no', 'name', 'status', 'marked_at', 'method']], 
                        use_container_width=True,
                        hide_index=True
                    )
                    
                    # Manual override section
                    st.subheader("✏️ Manual Override")
                    
                    with st.form("manual_override"):
                        col1, col2, col3 = st.columns([2, 1, 1])
                        
                        with col1:
                            student_options = {f"{row['roll_no']} - {row['name']}": row['roll_no'] 
                                             for _, row in df.iterrows()}
                            selected_student = st.selectbox("Select Student", list(student_options.keys()))
                        
                        with col2:
                            new_status = st.selectbox("New Status", ["Present", "Absent"])
                        
                        with col3:
                            reason = st.text_input("Reason (optional)")
                        
                        if st.form_submit_button("🔄 Update Attendance"):
                            try:
                                roll_no = student_options[selected_student]
                                response = requests.post(
                                    f"{api_base}/teacher/manual_override",
                                    json={
                                        "session_id": session_data['session']['session_id'],
                                        "roll_no": roll_no,
                                        "new_status": new_status,
                                        "teacher_id": st.session_state.teacher_token.split('.')[0],
                                        "reason": reason
                                    },
                                    headers=headers
                                )
                                
                                if response.status_code == 200:
                                    st.success("✅ Attendance updated successfully!")
                                    st.rerun()
                                else:
                                    st.error("❌ Failed to update attendance.")
                            except Exception as e:
                                st.error(f"❌ Error updating attendance: {e}")
                
                else:
                    st.info("No students have marked attendance yet.")
            
            else:
                st.error("Failed to fetch attendance data.")
        
        except Exception as e:
            st.error(f"Error fetching attendance: {e}")
    
    # Export section
    st.subheader("📥 Export Data")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("📊 Export All Attendance", use_container_width=True):
            try:
                response = requests.get(
                    f"{api_base}/export/attendance/{branch_code}",
                    headers=headers
                )
                
                if response.status_code == 200:
                    st.download_button(
                        label="💾 Download Attendance CSV",
                        data=response.content,
                        file_name=f"attendance_{branch_code}_all.csv",
                        mime="text/csv"
                    )
                else:
                    st.error("Failed to export attendance data.")
            except Exception as e:
                st.error(f"Error exporting data: {e}")
    
    with col2:
        if st.button("📈 Export Statistics", use_container_width=True):
            try:
                response = requests.get(
                    f"{api_base}/export/stats/{branch_code}",
                    headers=headers
                )
                
                if response.status_code == 200:
                    st.download_button(
                        label="💾 Download Stats CSV",
                        data=response.content,
                        file_name=f"stats_{branch_code}.csv",
                        mime="text/csv"
                    )
                else:
                    st.error("Failed to export statistics.")
            except Exception as e:
                st.error(f"Error exporting statistics: {e}")