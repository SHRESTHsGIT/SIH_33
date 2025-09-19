## config.py
import os
from pathlib import Path

# Base paths
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
BRANCHES_DIR = DATA_DIR / "branches"

# File paths
BRANCHES_CSV = DATA_DIR / "branches.csv"
TEACHERS_CSV = DATA_DIR / "teachers.csv"

# Security
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Face recognition settings
FACE_RECOGNITION_THRESHOLD = 0.7
MAX_FACE_DISTANCE = 0.6

# Session settings
DEFAULT_SESSION_DURATION_MINUTES = 60

# Timezone
TIMEZONE = "Asia/Kolkata"

# API settings
API_HOST = "localhost"
API_PORT = 8000

# Streamlit settings
STREAMLIT_HOST = "localhost"
STREAMLIT_PORT = 8501

# Create directories if they don't exist
def setup_directories():
    DATA_DIR.mkdir(exist_ok=True)
    BRANCHES_DIR.mkdir(exist_ok=True)
    
    # Create initial CSV files if they don't exist
    if not BRANCHES_CSV.exists():
        import pandas as pd
        df = pd.DataFrame({
            'branch_code': ['CSH', 'CSA', 'EEE'],
            'branch_name': ['CSE(HCI & Gaming Tech)', 'CSE(AIML)', 'Electrical & Electronics']
        })
        df.to_csv(BRANCHES_CSV, index=False)
    
    if not TEACHERS_CSV.exists():
        import pandas as pd
        from utils.crypto_utils import hash_password
        df = pd.DataFrame({
            'teacher_id': ['T001', 'T002'],
            'teacher_name': ['Prof. Sharma', 'Ms. Rao'],
            'password': [hash_password('password123'), hash_password('password456')]
        })
        df.to_csv(TEACHERS_CSV, index=False)

if __name__ == "__main__":
    setup_directories()
