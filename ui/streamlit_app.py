## ui/streamlit_app.py

import streamlit as st
import pandas as pd
import requests
from pathlib import Path
import sys

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from config import BRANCHES_CSV, API_HOST, API_PORT
from ui.pages import branch_dashboard, teacher_panel, student_registration, mark_attendance, stats_view

# Page configuration
st.set_page_config(
    page_title="Face Recognition Attendance System",
    page_icon="👥",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        text-align: center;
        padding: 1rem 0;
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        color: white;
        border-radius: 10px;
        margin-bottom: 2rem;
    }
    
    .status-card {
        padding: 1rem;
        border-radius: 8px;
        border-left: 4px solid #667eea;
        background-color: #f8f9fa;
        margin: 1rem 0;
    }
    
    .success-card {
        border-left-color: #28a745;
        background-color: #d4edda;
    }
    
    .warning-card {
        border-left-color: #ffc107;
        background-color: #fff3cd;
    }
    
    .error-card {
        border-left-color: #dc3545;
        background-color: #f8d7da;
    }
    
    .stButton > button {
        width: 100%;
        border-radius: 8px;
        border: none;
        padding: 0.5rem 1rem;
        font-weight: 600;
        transition: all 0.3s;
    }
    
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 8px rgba(0,0,0,0.2);
    }
    
    .countdown-timer {
        font-size: 1.5rem;
        font-weight: bold;
        color: #dc3545;
        text-align: center;
        padding: 1rem;
        background-color: #fff3cd;
        border-radius: 8px;
        border: 2px solid #ffc107;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'current_page' not in st.session_state:
    st.session_state.current_page = 'branch_select'

if 'selected_branch' not in st.session_state:
    st.session_state.selected_branch = None

if 'teacher_token' not in st.session_state:
    st.session_state.teacher_token = None

if 'teacher_name' not in st.session_state:
    st.session_state.teacher_name = None

# API base URL
API_BASE = f"http://{API_HOST}:{API_PORT}/api"

def get_branches():
    """Get list of branches from API"""
    try:
        response = requests.get(f"{API_BASE}/branches")
        if response.status_code == 200:
            return response.json()
        return []
    except Exception as e:
        st.error(f"Error fetching branches: {e}")
        return []

def get_active_session(branch_code):
    """Get active session for branch"""
    try:
        response = requests.get(f"{API_BASE}/session/{branch_code}/active")
        if response.status_code == 200:
            return response.json()
        return {"active": False}
    except Exception as e:
        st.error(f"Error fetching session: {e}")
        return {"active": False}

def main():
    """Main application function"""
    
    # Header
    st.markdown("""
    <div class="main-header">
        <h1>🎓 Face Recognition Attendance System</h1>
        <p>Secure, Fast, and Reliable Attendance Management</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Sidebar navigation
    with st.sidebar:
        st.title("📍 Navigation")
        
        # Branch selection
        if st.session_state.current_page == 'branch_select' or st.session_state.selected_branch is None:
            st.subheader("Select Branch")
            branches = get_branches()
            
            if branches:
                branch_options = {f"{b['branch_code']} - {b['branch_name']}": b['branch_code'] 
                                for b in branches}
                
                selected = st.selectbox("Choose your branch:", list(branch_options.keys()))
                
                if st.button("Select Branch", type="primary"):
                    st.session_state.selected_branch = branch_options[selected]
                    st.session_state.current_page = 'dashboard'
                    st.rerun()
            else:
                st.error("No branches available. Please check the system configuration.")
                return
        
        else:
            # Show current branch
            st.success(f"📚 Current Branch: **{st.session_state.selected_branch}**")
            
            if st.button("🔄 Change Branch"):
                st.session_state.selected_branch = None
                st.session_state.current_page = 'branch_select'
                st.session_state.teacher_token = None
                st.session_state.teacher_name = None
                st.session_state.teacher_id = None
                st.rerun()
            
            st.divider()
            
            # Navigation menu
            menu_items = {
                "🏠 Dashboard": "dashboard",
                "👨‍🏫 Teacher Panel": "teacher_panel",
                "📝 Register Student": "register_student",
                "✅ Mark Attendance": "mark_attendance",
                "📊 View Statistics": "stats"
            }
            
            for label, page in menu_items.items():
                if st.button(label):
                    st.session_state.current_page = page
                    st.rerun()
            
            st.divider()
            
            # Teacher status
            if st.session_state.teacher_token:
                st.success(f"👨‍🏫 Logged in as: **{st.session_state.teacher_name}**")
                if st.button("🚪 Logout"):
                    st.session_state.teacher_token = None
                    st.session_state.teacher_name = None
                    st.rerun()
            else:
                st.info("👤 Not logged in as teacher")
    
    # Main content area
    if st.session_state.current_page == 'branch_select' or st.session_state.selected_branch is None:
        st.info("👆 Please select a branch from the sidebar to continue.")
        
        # Show branch information
        st.subheader("📋 Available Branches")
        branches = get_branches()
        if branches:
            df = pd.DataFrame(branches)
            st.dataframe(df, use_container_width=True)
        else:
            st.warning("No branches configured in the system.")
    
    elif st.session_state.current_page == 'dashboard':
        branch_dashboard.show_dashboard(st.session_state.selected_branch, API_BASE)
    
    elif st.session_state.current_page == 'teacher_panel':
        teacher_panel.show_teacher_panel(st.session_state.selected_branch, API_BASE)
    
    elif st.session_state.current_page == 'register_student':
        student_registration.show_registration(st.session_state.selected_branch, API_BASE)
    
    elif st.session_state.current_page == 'mark_attendance':
        mark_attendance.show_attendance_marking(st.session_state.selected_branch, API_BASE)
    
    elif st.session_state.current_page == 'stats':
        stats_view.show_statistics(st.session_state.selected_branch, API_BASE)
    
    # Footer
    st.markdown("---")
    st.markdown("""
    <div style="text-align: center; color: #666; padding: 1rem;">
        <p>🔒 Secure Face Recognition Attendance System v1.0</p>
        <p>Built with ❤️ using Streamlit & FastAPI</p>
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
