## run.py-
import subprocess
import threading
import time
import sys
from config import setup_directories, API_HOST, API_PORT, STREAMLIT_HOST, STREAMLIT_PORT

def run_fastapi():
    """Run FastAPI server"""
    subprocess.run([
        sys.executable, "-m", "uvicorn", 
        "api.main:app", 
        "--host", API_HOST, 
        "--port", str(API_PORT),
        "--reload"
    ])

def run_streamlit():
    """Run Streamlit app"""
    subprocess.run([
        sys.executable, "-m", "streamlit", "run", 
        "ui/streamlit_app.py",
        "--server.address", STREAMLIT_HOST,
        "--server.port", str(STREAMLIT_PORT)
    ])

if __name__ == "__main__":
    # Setup directories and initial data
    setup_directories()
    
    print("Starting Face Recognition Attendance System...")
    print(f"FastAPI will run on http://{API_HOST}:{API_PORT}")
    print(f"Streamlit will run on http://{STREAMLIT_HOST}:{STREAMLIT_PORT}")
    
    # Start FastAPI in a separate thread
    api_thread = threading.Thread(target=run_fastapi, daemon=True)
    api_thread.start()
    
    # Give FastAPI time to start
    time.sleep(3)
    
    # Start Streamlit (main thread)
    run_streamlit()
