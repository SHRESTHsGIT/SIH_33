## ui/pages/mark_attendance.py

import streamlit as st
import requests
from PIL import Image
import io
import cv2
import numpy as np
from pyzbar import pyzbar
from datetime import datetime

def show_attendance_marking(branch_code, api_base):
    """Show attendance marking page"""
    
    st.title(f"✅ Mark Attendance - {branch_code}")
    
    # Check for active session
    try:
        response = requests.get(f"{api_base}/session/{branch_code}/active")
        session_data = response.json() if response.status_code == 200 else {"active": False}
    except Exception as e:
        st.error(f"Error checking session: {e}")
        session_data = {"active": False}
    
    if not session_data["active"]:
        st.markdown("""
        <div class="status-card error-card">
            <h4>❌ No Active Session</h4>
            <p>There is currently no active attendance session for this branch.</p>
            <p>Please wait for a teacher to start an attendance session.</p>
        </div>
        """, unsafe_allow_html=True)
        
        # Show when was the last session
        st.subheader("📅 Session Status")
        st.info("Contact your teacher to start an attendance session.")
        return
    
    # Active session - show countdown
    session = session_data["session"]
    deadline = datetime.fromisoformat(session['deadline_time'].replace('Z', '+00:00'))
    now = datetime.now()
    
    if now >= deadline:
        st.markdown("""
        <div class="status-card error-card">
            <h4>⏰ Session Expired</h4>
            <p>The attendance session has ended. You can no longer mark attendance.</p>
        </div>
        """, unsafe_allow_html=True)
        return
    
    # Show countdown timer
    remaining = deadline - now
    minutes = int(remaining.total_seconds() / 60)
    seconds = int(remaining.total_seconds() % 60)
    
    st.markdown(f"""
    <div class="countdown-timer">
        ⏰ Session ends in: {minutes:02d}:{seconds:02d}
    </div>
    """, unsafe_allow_html=True)
    
    # Attendance marking options
    st.subheader("📋 How would you like to mark attendance?")
    
    tab1, tab2 = st.tabs(["📸 Face Recognition", "📱 QR Code"])
    
    with tab1:
        show_face_recognition_tab(session['session_id'], branch_code, api_base)
    
    with tab2:
        show_qr_code_tab(session['session_id'], branch_code, api_base)

def show_face_recognition_tab(session_id, branch_code, api_base):
    """Show face recognition attendance marking"""
    
    st.markdown("""
    <div class="status-card">
        <h4>📸 Face Recognition Instructions</h4>
        <ul>
            <li>🎯 Position your face clearly in the camera</li>
            <li>💡 Ensure good lighting</li>
            <li>😊 Look directly at the camera</li>
            <li>📷 Capture a clear photo</li>
        </ul>
    </div>
    """, unsafe_allow_html=True)
    
    # Camera input
    camera_photo = st.camera_input("📷 Capture your photo for attendance")
    
    # Alternative file upload
    st.markdown("**Or upload a recent photo:**")
    uploaded_file = st.file_uploader(
        "📁 Choose a photo file", 
        type=['jpg', 'jpeg', 'png'],
        help="Upload a clear photo of your face"
    )
    
    # Mark attendance button
    photo_data = None
    if camera_photo is not None:
        photo_data = camera_photo.getvalue()
    elif uploaded_file is not None:
        photo_data = uploaded_file.getvalue()
    
    if photo_data:
        # Show preview
        try:
            image = Image.open(io.BytesIO(photo_data))
            st.image(image, caption="Photo for attendance", width=300)
        except:
            st.error("Invalid image file.")
            return
        
        if st.button("✅ Mark Attendance with Face", type="primary", use_container_width=True):
            mark_attendance_with_face(session_id, photo_data, api_base)

def show_qr_code_tab(session_id, branch_code, api_base):
    """Show QR code attendance marking"""
    
    st.markdown("""
    <div class="status-card">
        <h4>📱 QR Code Instructions</h4>
        <ul>
            <li>📱 Use your downloaded QR code</li>
            <li>📷 Scan the QR code with camera or upload the image</li>
            <li>✅ QR code will be verified automatically</li>
        </ul>
    </div>
    """, unsafe_allow_html=True)
    
    # QR scanning options
    qr_tab1, qr_tab2 = st.tabs(["📷 Scan QR", "📁 Upload QR"])
    
    with qr_tab1:
        qr_camera = st.camera_input("📷 Scan your QR code")
        
        if qr_camera is not None:
            qr_data = decode_qr_from_image(qr_camera.getvalue())
            if qr_data:
                st.success(f"✅ QR Code detected: {qr_data}")
                if st.button("✅ Mark Attendance with QR", type="primary", use_container_width=True):
                    mark_attendance_with_qr(session_id, qr_data, api_base)
            else:
                st.error("❌ No QR code detected. Please try again.")
    
    with qr_tab2:
        qr_file = st.file_uploader(
            "📁 Upload QR code image", 
            type=['jpg', 'jpeg', 'png'],
            help="Upload your QR code image"
        )
        
        if qr_file is not None:
            qr_data = decode_qr_from_image(qr_file.getvalue())
            if qr_data:
                st.success(f"✅ QR Code detected: {qr_data}")
                if st.button("✅ Mark Attendance with QR", type="primary", use_container_width=True, key="qr_upload"):
                    mark_attendance_with_qr(session_id, qr_data, api_base)
            else:
                st.error("❌ No QR code detected in uploaded image.")

def mark_attendance_with_face(session_id, photo_data, api_base):
    """Mark attendance using face recognition"""
    
    with st.spinner("🔍 Recognizing face..."):
        try:
            # Prepare form data
            files = {
                'face_image': ('face.jpg', photo_data, 'image/jpeg')
            }
            
            data = {
                'session_id': session_id,
                'method': 'face'
            }
            
            # Make API request
            response = requests.post(
                f"{api_base}/attendance/mark",
                files=files,
                data=data
            )
            
            if response.status_code == 200:
                result = response.json()
                
                if result['success']:
                    st.markdown(f"""
                    <div class="status-card success-card">
                        <h4>✅ Attendance Marked Successfully!</h4>
                        <p><strong>Message:</strong> {result['message']}</p>
                        <p><strong>Time:</strong> {result.get('marked_at', 'Now')}</p>
                        <p><strong>Method:</strong> Face Recognition</p>
                    </div>
                    """, unsafe_allow_html=True)
                
                elif result['already_marked']:
                    st.markdown(f"""
                    <div class="status-card warning-card">
                        <h4>⚠️ Already Marked</h4>
                        <p>You have already marked attendance for this session.</p>
                        <p><strong>Marked at:</strong> {result.get('marked_at', 'Earlier')}</p>
                        <p><strong>Method:</strong> {result.get('method', 'Unknown')}</p>
                    </div>
                    """, unsafe_allow_html=True)
                
                else:
                    st.markdown(f"""
                    <div class="status-card error-card">
                        <h4>❌ Face Not Recognized</h4>
                        <p>{result['message']}</p>
                        <p>Please try again or use QR code method.</p>
                    </div>
                    """, unsafe_allow_html=True)
            
            else:
                st.error(f"❌ Failed to mark attendance: {response.status_code}")
                
        except Exception as e:
            st.error(f"❌ Error marking attendance: {e}")

def mark_attendance_with_qr(session_id, qr_data, api_base):
    """Mark attendance using QR code"""
    
    with st.spinner("🔍 Verifying QR code..."):
        try:
            # Prepare form data
            data = {
                'session_id': session_id,
                'method': 'qr',
                'qr_data': qr_data
            }
            
            # Make API request
            response = requests.post(
                f"{api_base}/attendance/mark",
                data=data
            )
            
            if response.status_code == 200:
                result = response.json()
                
                if result['success']:
                    st.markdown(f"""
                    <div class="status-card success-card">
                        <h4>✅ Attendance Marked Successfully!</h4>
                        <p><strong>Message:</strong> {result['message']}</p>
                        <p><strong>Time:</strong> {result.get('marked_at', 'Now')}</p>
                        <p><strong>Method:</strong> QR Code</p>
                    </div>
                    """, unsafe_allow_html=True)
                
                elif result['already_marked']:
                    st.markdown(f"""
                    <div class="status-card warning-card">
                        <h4>⚠️ Already Marked</h4>
                        <p>You have already marked attendance for this session.</p>
                        <p><strong>Marked at:</strong> {result.get('marked_at', 'Earlier')}</p>
                        <p><strong>Method:</strong> {result.get('method', 'Unknown')}</p>
                    </div>
                    """, unsafe_allow_html=True)
                
                else:
                    st.markdown(f"""
                    <div class="status-card error-card">
                        <h4>❌ QR Code Invalid</h4>
                        <p>{result['message']}</p>
                        <p>Please check your QR code or try face recognition.</p>
                    </div>
                    """, unsafe_allow_html=True)
            
            else:
                st.error(f"❌ Failed to mark attendance: {response.status_code}")
                
        except Exception as e:
            st.error(f"❌ Error marking attendance: {e}")

def decode_qr_from_image(image_bytes):
    """Decode QR code from image bytes"""
    try:
        # Convert bytes to numpy array
        nparr = np.frombuffer(image_bytes, np.uint8)
        image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        if image is None:
            return None
        
        # Convert to grayscale for better QR detection
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # Decode QR codes
        qr_codes = pyzbar.decode(gray)
        
        if qr_codes:
            # Return the first QR code found
            return qr_codes[0].data.decode('utf-8')
        
        return None
    except Exception as e:
        print(f"Error decoding QR code: {e}")
        return None