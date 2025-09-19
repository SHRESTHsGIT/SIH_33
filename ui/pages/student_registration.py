# ui/pages/student_registration.py

import streamlit as st
import requests
from PIL import Image
import io
import re

def show_registration(branch_code, api_base):
    """Show student registration page"""

    st.title(f"📝 Student Registration - {branch_code}")

    st.markdown("""
    <div class="status-card">
        <h4>📋 Registration Instructions</h4>
        <ul>
            <li>🎯 Enter your roll number in the format: BT23CSH013</li>
            <li>📷 Capture a clear photo of your face</li>
            <li>🔍 Make sure your face is well-lit and clearly visible</li>
            <li>📱 You'll receive a QR code as backup for attendance</li>
        </ul>
    </div>
    """, unsafe_allow_html=True)

    # Registration form
    with st.form("student_registration"):
        st.subheader("📄 Student Information")

        col1, col2 = st.columns(2)

        with col1:
            roll_no = st.text_input(
                "🎓 Roll Number",
                placeholder="e.g., BT23CSH013",
                help="Format: BT + Year + Branch + Number"
            )

        with col2:
            name = st.text_input(
                "👤 Full Name",
                placeholder="Enter your full name"
            )

        st.subheader("📸 Face Photo")

        # Camera input
        camera_photo = st.camera_input("📷 Take a photo for face recognition")

        # Alternative file upload
        st.markdown("**Or upload a photo:**")
        uploaded_file = st.file_uploader(
            "📁 Choose a photo file",
            type=['jpg', 'jpeg', 'png'],
            help="Upload a clear photo of your face"
        )

        # Submit button
        if st.form_submit_button("📝 Register Student", type="primary", use_container_width=True):
            # Validation
            if not roll_no or not name:
                st.error("⚠️ Please fill in all required fields.")
                return

            # Validate roll number format
            if not validate_roll_number(roll_no):
                st.error("⚠️ Invalid roll number format. Use format like: BT23CSH013")
                return

            # Check for photo
            photo_data = None
            if camera_photo is not None:
                photo_data = camera_photo.getvalue()
            elif uploaded_file is not None:
                photo_data = uploaded_file.getvalue()
            else:
                st.error("⚠️ Please capture or upload a photo.")
                return

            # Validate image
            try:
                image = Image.open(io.BytesIO(photo_data))
                if image.size[0] < 100 or image.size[1] < 100:
                    st.error("⚠️ Image is too small. Please use a higher resolution photo.")
                    return
            except Exception as e:
                st.error(f"⚠️ Invalid image file: {e}")
                return

            # Register student
            register_student(roll_no, name, branch_code, photo_data, api_base)


def validate_roll_number(roll_no):
    """Validate roll number format (e.g., BT23CSH013)"""
    pattern = r'^[A-Z]{2}\d{2}[A-Z]{3}\d{3}$'
    return re.match(pattern, roll_no) is not None


def register_student(roll_no, name, branch_code, photo_data, api_base):
    """Send student registration request to API"""
    try:
        files = {"photo": ("face.jpg", photo_data, "image/jpeg")}
        data = {"roll_no": roll_no, "name": name, "branch_code": branch_code}
        response = requests.post(f"{api_base}/register", data=data, files=files)

        if response.status_code == 200:
            st.success("✅ Student registered successfully!")
            st.json(response.json())
        else:
            st.error(f"⚠️ Registration failed: {response.text}")
    except Exception as e:
        st.error(f"⚠️ Error during registration: {e}")
