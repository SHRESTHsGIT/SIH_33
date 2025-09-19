## services/face_service.py
import cv2
import numpy as np
from deepface import DeepFace
import pandas as pd
from pathlib import Path
import pickle
from typing import Dict, Any, List, Optional
import os
from api.utils import get_branch_files, ensure_branch_structure
from config import FACE_RECOGNITION_THRESHOLD, MAX_FACE_DISTANCE

class FaceService:
    def __init__(self):
        self.model_name = "VGG-Face"
        self.embeddings_cache = {}
    
    def extract_face_embedding(self, image_path: str) -> Optional[np.ndarray]:
        """Extract face embedding from image"""
        try:
            # Use DeepFace to extract embedding
            embedding = DeepFace.represent(
                img_path=image_path,
                model_name=self.model_name,
                enforce_detection=False
            )
            
            if embedding and len(embedding) > 0:
                return np.array(embedding[0]["embedding"])
            return None
        except Exception as e:
            print(f"Error extracting embedding from {image_path}: {e}")
            return None
    
    def extract_face_embedding_from_bytes(self, image_bytes: bytes) -> Optional[np.ndarray]:
        """Extract face embedding from image bytes"""
        try:
            # Convert bytes to numpy array
            nparr = np.frombuffer(image_bytes, np.uint8)
            image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            if image is None:
                return None
            
            # Save temporarily for DeepFace processing
            temp_path = "/tmp/temp_face.jpg"
            cv2.imwrite(temp_path, image)
            
            # Extract embedding
            embedding = self.extract_face_embedding(temp_path)
            
            # Clean up temp file
            if os.path.exists(temp_path):
                os.remove(temp_path)
            
            return embedding
        except Exception as e:
            print(f"Error extracting embedding from bytes: {e}")
            return None
    
    def calculate_distance(self, embedding1: np.ndarray, embedding2: np.ndarray) -> float:
        """Calculate cosine distance between two embeddings"""
        try:
            # Normalize embeddings
            embedding1_norm = embedding1 / np.linalg.norm(embedding1)
            embedding2_norm = embedding2 / np.linalg.norm(embedding2)
            
            # Calculate cosine similarity
            cosine_similarity = np.dot(embedding1_norm, embedding2_norm)
            
            # Convert to distance (0 = identical, 1 = completely different)
            distance = 1 - cosine_similarity
            
            return distance
        except Exception as e:
            print(f"Error calculating distance: {e}")
            return 1.0  # Return max distance on error
    
    def load_embeddings(self, branch_code: str) -> Dict[str, np.ndarray]:
        """Load face embeddings for a branch"""
        if branch_code in self.embeddings_cache:
            return self.embeddings_cache[branch_code]
        
        try:
            files = get_branch_files(branch_code)
            embeddings_file = files['faces'].parent / f"embeddings_{branch_code}.pkl"
            
            if embeddings_file.exists():
                with open(embeddings_file, 'rb') as f:
                    embeddings = pickle.load(f)
                    self.embeddings_cache[branch_code] = embeddings
                    return embeddings
            
            return {}
        except Exception as e:
            print(f"Error loading embeddings: {e}")
            return {}
    
    def save_embeddings(self, branch_code: str, embeddings: Dict[str, np.ndarray]) -> None:
        """Save face embeddings for a branch"""
        try:
            files = get_branch_files(branch_code)
            embeddings_file = files['faces'].parent / f"embeddings_{branch_code}.pkl"
            
            with open(embeddings_file, 'wb') as f:
                pickle.dump(embeddings, f)
            
            # Update cache
            self.embeddings_cache[branch_code] = embeddings
        except Exception as e:
            print(f"Error saving embeddings: {e}")
    
    def update_embeddings(self, branch_code: str) -> None:
        """Update embeddings for all students in a branch"""
        try:
            ensure_branch_structure(branch_code)
            files = get_branch_files(branch_code)
            
            # Get students data
            students_df = pd.read_csv(files['students'])
            
            embeddings = {}
            
            for _, student in students_df.iterrows():
                roll_no = student['roll_no']
                face_path = student['face_path']
                
                if pd.notna(face_path) and Path(face_path).exists():
                    embedding = self.extract_face_embedding(face_path)
                    if embedding is not None:
                        embeddings[roll_no] = embedding
                        print(f"Updated embedding for {roll_no}")
                    else:
                        print(f"Failed to extract embedding for {roll_no}")
            
            # Save embeddings
            self.save_embeddings(branch_code, embeddings)
            print(f"Updated {len(embeddings)} embeddings for branch {branch_code}")
            
        except Exception as e:
            print(f"Error updating embeddings: {e}")
    
    def recognize_face(self, image_bytes: bytes, branch_code: str) -> Dict[str, Any]:
        """Recognize face from image bytes"""
        try:
            # Extract embedding from input image
            input_embedding = self.extract_face_embedding_from_bytes(image_bytes)
            
            if input_embedding is None:
                return {
                    'success': False,
                    'message': 'No face detected in image',
                    'roll_no': None,
                    'confidence': 0.0
                }
            
            # Load stored embeddings
            stored_embeddings = self.load_embeddings(branch_code)
            
            if not stored_embeddings:
                return {
                    'success': False,
                    'message': 'No registered faces found for this branch',
                    'roll_no': None,
                    'confidence': 0.0
                }
            
            # Find best match
            best_match = None
            best_distance = float('inf')
            
            for roll_no, stored_embedding in stored_embeddings.items():
                distance = self.calculate_distance(input_embedding, stored_embedding)
                
                if distance < best_distance:
                    best_distance = distance
                    best_match = roll_no
            
            # Check if match is good enough
            if best_distance <= MAX_FACE_DISTANCE:
                confidence = 1 - best_distance  # Convert distance to confidence
                return {
                    'success': True,
                    'message': f'Face recognized as {best_match}',
                    'roll_no': best_match,
                    'confidence': confidence,
                    'distance': best_distance
                }
            else:
                return {
                    'success': False,
                    'message': 'Face not recognized',
                    'roll_no': None,
                    'confidence': 1 - best_distance,
                    'distance': best_distance
                }
                
        except Exception as e:
            print(f"Error in face recognition: {e}")
            return {
                'success': False,
                'message': f'Error during recognition: {str(e)}',
                'roll_no': None,
                'confidence': 0.0
            }
    
    def verify_face(self, image_bytes: bytes, roll_no: str, branch_code: str) -> Dict[str, Any]:
        """Verify if image matches a specific student"""
        try:
            # Extract embedding from input image
            input_embedding = self.extract_face_embedding_from_bytes(image_bytes)
            
            if input_embedding is None:
                return {
                    'success': False,
                    'message': 'No face detected in image',
                    'verified': False,
                    'confidence': 0.0
                }
            
            # Load stored embeddings
            stored_embeddings = self.load_embeddings(branch_code)
            
            if roll_no not in stored_embeddings:
                return {
                    'success': False,
                    'message': 'Student not found in registered faces',
                    'verified': False,
                    'confidence': 0.0
                }
            
            # Calculate distance
            stored_embedding = stored_embeddings[roll_no]
            distance = self.calculate_distance(input_embedding, stored_embedding)
            
            # Verify match
            verified = distance <= MAX_FACE_DISTANCE
            confidence = 1 - distance
            
            return {
                'success': True,
                'message': f'Verification {"successful" if verified else "failed"}',
                'verified': verified,
                'confidence': confidence,
                'distance': distance
            }
            
        except Exception as e:
            print(f"Error in face verification: {e}")
            return {
                'success': False,
                'message': f'Error during verification: {str(e)}',
                'verified': False,
                'confidence': 0.0
            }