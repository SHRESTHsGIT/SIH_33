## services/qr_service.py

import qrcode
from pyzbar import pyzbar
import cv2
import numpy as np
from PIL import Image
from pathlib import Path
from typing import Dict, Any, Optional
import pandas as pd
from api.utils import get_branch_files
from utils.crypto_utils import generate_qr_signature, verify_qr_signature

class QRService:
    def __init__(self):
        self.use_signature = True  # Enable QR signature verification
    
    def generate_qr_code(self, roll_no: str, branch_code: str, output_path: str) -> bool:
        """Generate QR code for a student"""
        try:
            # Create QR data with optional signature
            if self.use_signature:
                signature = generate_qr_signature(roll_no, branch_code)
                qr_data = f"{roll_no}|{branch_code}|{signature}"
            else:
                qr_data = roll_no
            
            # Create QR code
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=10,
                border=4,
            )
            qr.add_data(qr_data)
            qr.make(fit=True)
            
            # Create QR code image
            qr_image = qr.make_image(fill_color="black", back_color="white")
            
            # Save image
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            qr_image.save(output_path)
            
            return True
        except Exception as e:
            print(f"Error generating QR code: {e}")
            return False
    
    def decode_qr_from_image(self, image_bytes: bytes) -> Optional[str]:
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
    
    def decode_qr_data(self, qr_data: str, branch_code: str) -> Dict[str, Any]:
        """Decode and validate QR data"""
        try:
            # Parse QR data
            parts = qr_data.split('|')
            
            if len(parts) == 1:
                # Simple format: just roll number
                roll_no = parts[0].strip()
                
                # Validate student exists in branch
                if self.validate_student_exists(roll_no, branch_code):
                    return {
                        'success': True,
                        'roll_no': roll_no,
                        'message': 'QR code decoded successfully'
                    }
                else:
                    return {
                        'success': False,
                        'roll_no': None,
                        'message': 'Student not found in this branch'
                    }
            
            elif len(parts) == 3:
                # Signed format: roll_no|branch_code|signature
                roll_no = parts[0].strip()
                qr_branch_code = parts[1].strip()
                signature = parts[2].strip()
                
                # Verify signature
                if not verify_qr_signature(roll_no, qr_branch_code, signature):
                    return {
                        'success': False,
                        'roll_no': None,
                        'message': 'Invalid QR code signature'
                    }
                
                # Verify branch matches
                if qr_branch_code != branch_code:
                    return {
                        'success': False,
                        'roll_no': None,
                        'message': 'QR code is for different branch'
                    }
                
                # Validate student exists
                if self.validate_student_exists(roll_no, branch_code):
                    return {
                        'success': True,
                        'roll_no': roll_no,
                        'message': 'QR code decoded and verified successfully'
                    }
                else:
                    return {
                        'success': False,
                        'roll_no': None,
                        'message': 'Student not found in this branch'
                    }
            
            else:
                return {
                    'success': False,
                    'roll_no': None,
                    'message': 'Invalid QR code format'
                }
                
        except Exception as e:
            print(f"Error decoding QR data: {e}")
            return {
                'success': False,
                'roll_no': None,
                'message': f'Error decoding QR code: {str(e)}'
            }
    
    def validate_student_exists(self, roll_no: str, branch_code: str) -> bool:
        """Validate if student exists in branch"""
        try:
            files = get_branch_files(branch_code)
            if not files['students'].exists():
                return False
            
            students_df = pd.read_csv(files['students'])
            return roll_no in students_df['roll_no'].values
        except Exception:
            return False