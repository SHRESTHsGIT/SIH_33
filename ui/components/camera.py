## ui/components/camera.py

import streamlit as st
import cv2
import numpy as np
from PIL import Image
import io

class CameraComponent:
    """Camera component for capturing images"""
    
    def __init__(self):
        self.camera = None
    
    def capture_image(self, key="camera", help_text="Capture image"):
        """Capture image using Streamlit camera input"""
        return st.camera_input(help_text, key=key)
    
    def process_image(self, image_data, target_size=(400, 400)):
        """Process captured image"""
        try:
            # Convert to PIL Image
            image = Image.open(io.BytesIO(image_data))
            
            # Resize if needed
            if target_size:
                image = image.resize(target_size, Image.Resampling.LANCZOS)
            
            # Convert to bytes
            img_byte_arr = io.BytesIO()
            image.save(img_byte_arr, format='JPEG', quality=85)
            
            return img_byte_arr.getvalue()
            
        except Exception as e:
            st.error(f"Error processing image: {e}")
            return None
    
    def validate_image(self, image_data, min_size=(100, 100)):
        """Validate captured image"""
        try:
            image = Image.open(io.BytesIO(image_data))
            
            # Check size
            if image.size[0] < min_size[0] or image.size[1] < min_size[1]:
                return False, "Image is too small"
            
            # Check format
            if image.format not in ['JPEG', 'PNG', 'JPG']:
                return False, "Invalid image format"
            
            return True, "Image is valid"
            
        except Exception as e:
            return False, f"Error validating image: {e}"