## ui/pages/stats_view.py
import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta

def show_statistics(branch_code, api_base):
    """Show attendance statistics"""
    
    st.title(f"📊 Attendance Statistics - {branch_code}")
    
    # Fetch statistics
    try:
        response = requests.get(f"{api_base}/stats/{branch_code}")
        
        if response.status_code == 200:
            stats_data = response.json()
            
            if not stats_data:
                st.info("📊 No statistics available yet. Start taking attendance to see data.")
                return
            
            df = pd.DataFrame(stats_data)
            
            # Overview metrics
            show_overview_metrics(df)
            
            # Charts and visualizations
            show_attendance_charts(df)
            
            # Detailed statistics table
            show_detailed_table(df)
            
            # Export options
            show_export_options(branch_code, api_base)
            
        else:
            st.error("Failed to fetch statistics.")
            
    except Exception as e:
        st.error(f"Error fetching statistics: {e}")

def show_overview_metrics(df):
    """Show overview metrics"""
    
    st.subheader("📈 Overview")
    
    # Calculate metrics
    total_students = len(df)
    avg_attendance = df['attendance_pct'].mean()
    
    # Find best and worst performers
    best_student = df.loc[df['attendance_pct'].idxmax()] if not df.empty else None
    worst_student = df.loc[df['attendance_pct'].idxmin()] if not df.empty else None
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "👥 Total Students", 
            total_students,
            help="Number of registered students"
        )
    
    with col2:
        st.metric(
            "📊 Average Attendance", 
            f"{avg_attendance:.1f}%",
            help="Average attendance percentage across all students"
        )
    
    with col3:
        if best_student is not None:
            st.metric(
                "🏆 Best Attendance", 
                f"{best_student['attendance_pct']:.1f}%",
                help=f"Best performer: {best_student['name']}"
            )
    
    with col4:
        total_sessions = df['total_days'].max() if not df.empty else 0
        st.metric(
            "📅 Total Sessions", 
            total_sessions,
            help="Total number of attendance sessions conducted"
        )

def show_attendance_charts(df):
    """Show attendance charts and visualizations"""
    
    st.subheader("📊 Visualizations")
    
    tab1, tab2, tab3 = st.tabs(["📈 Distribution", "🏆 Top Performers", "📉 Trends"])
    
    with tab1:
        # Attendance distribution histogram
        fig_hist = px.histogram(
            df, 
            x='attendance_pct', 
            nbins=20,
            title="Attendance Percentage Distribution",
            labels={'attendance_pct': 'Attendance Percentage (%)', 'count': 'Number of Students'},
            color_discrete_sequence=['#667eea']
        )
        fig_hist.update_layout(showlegend=False)
        st.plotly_chart(fig_hist, use_container_width=True)
        
        # Attendance categories
        excellent = len(df[df['attendance_pct'] >= 90])
        good = len(df[(df['attendance_pct'] >= 75) & (df['attendance_pct'] < 90)])
        average = len(df[(df['attendance_pct'] >= 60) & (df['attendance_pct'] < 75)])
        poor = len(df[df['attendance_pct'] < 60])
        
        fig_pie = go.Figure(data=[go.Pie(
            labels=['Excellent (≥90%)', 'Good (75-89%)', 'Average (60-74%)', 'Poor (<60%)'],
            values=[excellent, good, average, poor],
            hole=.3,
            marker_colors=['#28a745', '#17a2b8', '#ffc107', '#dc3545']
        )])
        fig_pie.update_layout(title="Attendance Categories")
        st.plotly_chart(fig_pie, use_container_width=True)
    
    with tab2:
        # Top 10 performers
        top_10 = df.nlargest(10, 'attendance_pct')
        
        fig_bar = px.bar(
            top_10,
            x='attendance_pct',
            y='name',
            orientation='h',
            title="Top 10 Students by Attendance",
            labels={'attendance_pct': 'Attendance Percentage (%)', 'name': 'Student Name'},
            color='attendance_pct',
            color_continuous_scale='Viridis'
        )
        fig_bar.update_layout(yaxis={'categoryorder': 'total ascending'})
        st.plotly_chart(fig_bar, use_container_width=True)
        
        # Performance summary table
        st.markdown("**🏆 Top Performers Summary**")
        top_5 = df.nlargest(5, 'attendance_pct')[['roll_no', 'name', 'attendance_pct', 'present_days', 'total_days']]
        st.dataframe(top_5, use_container_width=True, hide_index=True)
    
    with tab3:
        # Present vs Absent comparison
        fig_comparison = go.Figure()
        
        fig_comparison.add_trace(go.Bar(
            name='Present Days',
            x=df['name'][:10],  # Show first 10 students
            y=df['present_days'][:10],
            marker_color='#28a745'
        ))
        
        fig_comparison.add_trace(go.Bar(
            name='Absent Days',
            x=df['name'][:10],
            y=df['absent_days'][:10],
            marker_color='#dc3545'
        ))
        
        fig_comparison.update_layout(
            title="Present vs Absent Days (First 10 Students)",
            xaxis_title="Student Name",
            yaxis_title="Number of Days",
            barmode='stack'
        )
        st.plotly_chart(fig_comparison, use_container_width=True)
        
        # Attendance trend over time (if we had date-wise data)
        st.info("📅 Detailed trend analysis will be available with more historical data.")

def show_detailed_table(df):
    """Show detailed statistics table"""
    
    st.subheader("📋 Detailed Statistics")
    
    # Search and filter options
    col1, col2 = st.columns([2, 1])
    
    with col1:
        search_term = st.text_input("🔍 Search students", placeholder="Enter name or roll number")
    
    with col2:
        min_attendance = st.slider("Minimum Attendance %", 0, 100, 0)
    
    # Filter data
    filtered_df = df.copy()
    
    if search_term:
        filtered_df = filtered_df[
            filtered_df['name'].str.contains(search_term, case=False) |
            filtered_df['roll_no'].str.contains(search_term, case=False)
        ]
    
    filtered_df = filtered_df[filtered_df['attendance_pct'] >= min_attendance]
    
    # Sort options
    sort_by = st.selectbox(
        "📊 Sort by",
        ['attendance_pct', 'present_days', 'absent_days', 'name', 'roll_no'],
        format_func=lambda x: {
            'attendance_pct': 'Attendance Percentage',
            'present_days': 'Present Days',
            'absent_days': 'Absent Days',
            'name': 'Name',
            'roll_no': 'Roll Number'
        }[x]
    )
    
    sort_order = st.radio("Sort order", ['Descending', 'Ascending'], horizontal=True)
    ascending = sort_order == 'Ascending'
    
    # Apply sorting
    filtered_df = filtered_df.sort_values(sort_by, ascending=ascending)
    
    # Display table
    if not filtered_df.empty:
        # Prepare display data
        display_df = filtered_df[[
            'roll_no', 'name', 'present_days', 'absent_days', 
            'total_days', 'attendance_pct', 'last_present', 'last_absent'
        ]].copy()
        
        # Format columns
        display_df['attendance_pct'] = display_df['attendance_pct'].apply(lambda x: f"{x:.1f}%")
        display_df['last_present'] = pd.to_datetime(display_df['last_present']).dt.strftime('%Y-%m-%d').fillna('Never')
        display_df['last_absent'] = pd.to_datetime(display_df['last_absent']).dt.strftime('%Y-%m-%d').fillna('Never')
        
        # Rename columns for display
        display_df.columns = [
            'Roll No', 'Name', 'Present', 'Absent', 
            'Total', 'Attendance %', 'Last Present', 'Last Absent'
        ]
        
        st.dataframe(display_df, use_container_width=True, hide_index=True)
        
        st.info(f"Showing {len(filtered_df)} of {len(df)} students")
        
    else:
        st.warning("No students match the current filters.")

def show_export_options(branch_code, api_base):
    """Show export options"""
    
    st.subheader("💾 Export Data")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("📊 Export Statistics CSV", use_container_width=True):
            try:
                response = requests.get(f"{api_base}/export/stats/{branch_code}")
                
                if response.status_code == 200:
                    st.download_button(
                        label="💾 Download Statistics",
                        data=response.content,
                        file_name=f"statistics_{branch_code}_{datetime.now().strftime('%Y%m%d')}.csv",
                        mime="text/csv",
                        use_container_width=True
                    )
                else:
                    st.error("Failed to export statistics.")
            except Exception as e:
                st.error(f"Export error: {e}")
    
    with col2:
        if st.button("📋 Export Full Attendance", use_container_width=True):
            try:
                response = requests.get(f"{api_base}/export/attendance/{branch_code}")
                
                if response.status_code == 200:
                    st.download_button(
                        label="💾 Download Full Attendance",
                        data=response.content,
                        file_name=f"attendance_{branch_code}_{datetime.now().strftime('%Y%m%d')}.csv",
                        mime="text/csv",
                        use_container_width=True
                    )
                else:
                    st.error("Failed to export attendance data.")
            except Exception as e:
                st.error(f"Export error: {e}")