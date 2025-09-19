## ui/components/face_recognition.py

import streamlit as st
import cv2
import numpy as np
from PIL import Image
import io

class FaceRecognitionComponent:
    """Face recognition UI component"""
    
    def __init__(self):
        pass
    
    def capture_face(self, key="face_camera", instructions=True):
        """Capture face image with instructions"""
        
        if instructions:
            self.show_face_instructions()
        
        return st.camera_input("📷 Capture your face", key=key)
    
    def upload_face(self, key="face_upload"):
        """Upload face image"""
        return st.file_uploader(
            "📁 Upload face image",
            type=['jpg', 'jpeg', 'png'],
            help="Upload a clear photo of your face",
            key=key
        )
    
    def show_face_instructions(self):
        """Show face capture instructions"""
        st.markdown("""
        **📸 Face Recognition Instructions:**
        - 🎯 Position your face in the center of the frame
        - 💡 Ensure good, even lighting on your face
        - 😊 Look directly at the camera
        - 🚫 Avoid shadows, glare, or obstructions
        - 📏 Keep a normal distance from the camera
        """)
    
    def validate_face_image(self, image_data):
        """Basic validation of face image"""
        try:
            image = Image.open(io.BytesIO(image_data))
            
            # Convert to OpenCV format for face detection
            cv_image = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
            
            # Load face cascade classifier
            face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
            
            # Convert to grayscale
            gray = cv2.cvtColor(cv_image, cv2.COLOR_BGR2GRAY)
            
            # Detect faces
            faces = face_cascade.detectMultiScale(gray, 1.1, 4)
            
            if len(faces) == 0:
                return False, "No face detected in the image"
            elif len(faces) > 1:
                return False, "Multiple faces detected. Please ensure only one face is visible"
            else:
                # Check face size
                x, y, w, h = faces[0]
                face_area = w * h
                image_area = image.size[0] * image.size[1]
                face_ratio = face_area / image_area
                
                if face_ratio < 0.05:
                    return False, "Face is too small in the image"
                elif face_ratio > 0.8:
                    return False, "Face is too close to the camera"
                else:
                    return True, "Face detected successfully"
                    
        except Exception as e:
            return False, f"Error validating image: {e}"
    
    def show_face_preview(self, image_data, max_width=300):
        """Show preview of captured face"""
        try:
            image = Image.open(io.BytesIO(image_data))
            st.image(image, caption="Captured Face", width=max_width)
            
            # Validate and show feedback
            is_valid, message = self.validate_face_image(image_data)
            
            if is_valid:
                st.success(f"✅ {message}")
            else:
                st.warning(f"⚠️ {message}")
            
            return is_valid
            
        except Exception as e:
            st.error(f"Error displaying image: {e}")
            return False