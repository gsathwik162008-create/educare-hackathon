"""
Smart Campus Analytics - Home & Role Routing
Handles role landing overviews.
"""

import streamlit as st
from core.ui import load_css

load_css()

user = st.session_state.get("user")
if not st.session_state.get("authenticated") or not user:
    st.error("Authentication Required: Please log in on the main portal page.")
    st.stop()

role = user.get("role", "").upper()

if role == "FACULTY":
    st.title("Faculty Advisory Portal")
    st.info(f"Signed in as advisor {user['name']} ({user['mentor_id']}).")
    st.markdown("""
    ### Advisory Workspaces
    - **Faculty Queue**: Prioritized mentee intervention tasks and lifecycle progression.
    - **Student Profile**: Individual student diagnostics, trends, and what-if simulation.
    """)

elif role == "ADMIN":
    st.title("Institution Administration Console")
    st.info(f"Signed in as {user['name']} with global cohort oversight.")
    st.markdown("""
    ### Available Workspaces
    - **Faculty Queue**: Full institution-wide intervention backlog across departments.
    - **Student Profile**: Deep-dive performance diagnostics and what-if simulation for any student.
    """)

elif role == "STUDENT":
    st.title("Student Growth Portal")
    st.info(f"Welcome, {user['name']} (Roll ID: {user['student_id']}).")
    st.markdown("""
    Your personalized academic indicators and growth milestones are scoped strictly to your account.
    Student profile details will become active in Phase 4 Part 3.
    """)

else:
    st.error("Unrecognized user role. Please sign in with valid credentials.")
