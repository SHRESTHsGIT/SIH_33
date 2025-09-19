## ui/components/qr_handler.py

import streamlit as st
import qrcode
from pyzbar import pyzbar
import cv2
import numpy as np
from PIL import Image
import io

class QRHandler:
    """QR code handling component"""
    
    def __init__(self):
        pass
    
    def generate_qr_display(self, data, size=(200, 200)):
        """Generate and display QR code"""
        try:
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=10,
                border=4,
            )
            qr.add_data(data)
            qr.make(fit=True)
            
            # Create QR code image
            qr_image = qr.make_image(fill_color="black", back_color="white")
            qr_image = qr_image.resize(size, Image.Resampling.LANCZOS)
            
            return qr_image
            
        except Exception as e:
            st.error(f"Error generating QR code: {e}")
            return None
    
    def decode_qr_from_camera(self, camera_key="qr_camera"):
        """Decode QR from camera input"""
        camera_input = st.camera_input("Scan QR Code", key=camera_key)
        
        if camera_input is not None:
            return self.decode_qr_from_bytes(camera_input.getvalue())
        
        return None
    
    def decode_qr_from_upload(self, upload_key="qr_upload"):
        """Decode QR from file upload"""
        uploaded_file = st.file_uploader(
            "Upload QR Code Image", 
            type=['jpg', 'jpeg', 'png'],
            key=upload_key
        )
        
        if uploaded_file is not None:
            return self.decode_qr_from_bytes(uploaded_file.getvalue())
        
        return None
    
    def decode_qr_from_bytes(self, image_bytes):
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
            st.error(f"Error decoding QR code: {e}")
            return None
    
    def show_qr_instructions(self):
        """Show QR code usage instructions"""
        st.markdown("""
        **📱 QR Code Instructions:**
        1. Use your downloaded QR code from registration
        2. Position the QR code clearly in the camera view
        3. Ensure good lighting and focus
        4. The system will automatically detect and verify the code
        """)