import streamlit as st
import requests
from datetime import datetime, timedelta
import pandas as pd

def show_teacher_panel(branch_code, api_base):
    """Show teacher panel"""
    st.title(f"👨‍🏫 Teacher Panel - {branch_code}")

    # Check if teacher is logged in
    if not st.session_state.get("teacher_token"):
        show_login_form(api_base)
    else:
        show_teacher_dashboard(branch_code, api_base)

def show_login_form(api_base):
    """Show teacher login form"""
    st.subheader("🔑 Teacher Login")

    with st.form("teacher_login"):
        teacher_id = st.text_input("👤 Teacher ID", placeholder="Enter your teacher ID")
        password = st.text_input("🔒 Password", type="password", placeholder="Enter your password")

        if st.form_submit_button("🚪 Login", use_container_width=True):
            if teacher_id and password:
                try:
                    response = requests.post(
                        f"{api_base}/teacher/login",
                        json={"teacher_id": teacher_id, "password": password}
                    )
                    if response.status_code == 200:
                        data = response.json()
                        st.session_state.teacher_token = data["access_token"]
                        st.session_state.teacher_name = data["teacher_name"]
                        st.success(f"✅ Welcome, {data['teacher_name']}!")
                        st.rerun()
                    else:
                        st.error("❌ Invalid credentials. Please try again.")
                except Exception as e:
                    st.error(f"❌ Login failed: {e}")
            else:
                st.warning("⚠️ Please enter both Teacher ID and Password.")

    with st.expander("🔍 Demo Credentials"):
        st.info("""
        **Demo Teacher Accounts:**
        - Teacher ID: T001, Password: password123
        - Teacher ID: T002, Password: password456
        """)

def show_teacher_dashboard(branch_code, api_base):
    """Show teacher dashboard after login"""
    headers = {"Authorization": f"Bearer {st.session_state.teacher_token}"}

    try:
        response = requests.get(f"{api_base}/session/{branch_code}/active")
        session_data = response.json() if response.status_code == 200 else {"active": False}
    except Exception as e:
        st.error(f"Error fetching session data: {e}")
        session_data = {"active": False}

    st.subheader("📅 Session Management")

    if not session_data["active"]:
        st.markdown("**🚀 Start New Attendance Session**")

        col1, col2 = st.columns([2, 1])
        with col1:
            deadline_minutes = st.slider(
                "⏰ Session Duration (minutes)",
                min_value=5,
                max_value=480,
                value=60,
                step=5
            )
        with col2:
            st.write("**Session will end at:**")
            end_time = datetime.now() + timedelta(minutes=deadline_minutes)
            st.info(end_time.strftime("%H:%M"))

        if st.button("🚀 Start Session", type="primary", use_container_width=True):
            try:
                response = requests.post(
                    f"{api_base}/teacher/start_session",
                    json={
                        "teacher_id": st.session_state.teacher_token.split('.')[0],
                        "branch_code": branch_code,
                        "deadline_minutes": deadline_minutes
                    },
                    headers=headers
                )
                if response.status_code == 200:
                    data = response.json()
                    st.success(f"✅ Session started! ID: {data['session_id']}")
                    st.rerun()
                else:
                    error_data = response.json()
                    st.error(f"❌ Failed to start session: {error_data.get('detail', 'Unknown error')}")
            except Exception as e:
                st.error(f"❌ Error starting session: {e}")
    else:
        session = session_data["session"]
        st.success("✅ **Active Session Running**")
        col1, col2 = st.columns(2)
        with col1:
            st.info(f"**Session ID:** {session['session_id']}")
            st.info(f"**Started:** {session['start_time']}")
        with col2:
            st.info(f"**Ends At:** {session['end_time']}")

def register_student(roll_no, name, branch_code, photo_data, api_base):
    """Register a new student"""
    with st.spinner("📝 Registering student..."):
        try:
            files = {'face_image': ('face.jpg', photo_data, 'image/jpeg')}
            data = {'roll_no': roll_no.upper(), 'name': name, 'branch_code': branch_code}

            response = requests.post(f"{api_base}/students/register", files=files, data=data)

            if response.status_code == 200:
                result = response.json()
                st.success("✅ Student registered successfully!")

                if 'qr_code_path' in result:
                    st.subheader("📱 Your QR Code")
                    st.info("💡 Download your QR code as backup for attendance marking.")
                    try:
                        qr_response = requests.get(f"{api_base}/download/qr/{branch_code}/{roll_no.upper()}")
                        if qr_response.status_code == 200:
                            st.download_button(
                                label="📱 Download QR Code",
                                data=qr_response.content,
                                file_name=f"{roll_no.upper()}_qr.png",
                                mime="image/png",
                                use_container_width=True
                            )
                        else:
                            st.warning("QR code generated but download failed. Contact admin.")
                    except Exception as e:
                        st.warning(f"QR code download error: {e}")

                st.markdown(f"""
                <div class="status-card success-card">
                    <h4>✅ Registration Complete</h4>
                    <p><strong>Roll Number:</strong> {roll_no.upper()}</p>
                    <p><strong>Name:</strong> {name}</p>
                    <p><strong>Branch:</strong> {branch_code}</p>
                    <p>You can now mark attendance when sessions are active!</p>
                </div>
                """, unsafe_allow_html=True)
            elif response.status_code == 400:
                error_data = response.json()
                if "already registered" in error_data.get('detail', '').lower():
                    st.error("⚠️ This student is already registered!")
                else:
                    st.error(f"⚠️ Registration failed: {error_data.get('detail', 'Unknown error')}")
            else:
                st.error(f"⚠️ Registration failed. Server error: {response.status_code}")
        except Exception as e:
            st.error(f"⚠️ Registration failed: {e}")

    st.subheader("👥 Registered Students")
    try:
        response = requests.get(f"{api_base}/students/{branch_code}")
        if response.status_code == 200:
            students = response.json()
            if students:
                student_data = [
                    {'Roll No': s['roll_no'], 'Name': s['name'], 'Registered On': s['registered_on'][:10]}
                    for s in students
                ]
                df = pd.DataFrame(student_data)
                st.dataframe(df, use_container_width=True, hide_index=True)
                st.info(f"📊 Total registered students: {len(students)}")
            else:
                st.info("No students registered yet for this branch.")
        else:
            st.warning("Could not fetch student list.")
    except Exception as e:
        st.error(f"Error fetching students: {e}")
