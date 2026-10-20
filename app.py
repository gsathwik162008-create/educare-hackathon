"""
Smart Campus Analytics - Main Entry Point & Authentication Hub
Handles user login, bcrypt authentication, session state management,
and role-based routing for ADMIN, FACULTY, and STUDENT users.
"""

import streamlit as st
import pandas as pd
from core.auth import authenticate_user
from core.ui import load_css, render_demo_badge

# Streamlit Page Config (no emoji)
st.set_page_config(
    page_title="Smart Campus Analytics | Login",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Load Institutional Design System
load_css()

# Session State Initialization
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False
if "user" not in st.session_state:
    st.session_state["user"] = None

def logout():
    st.session_state["authenticated"] = False
    st.session_state["user"] = None
    st.rerun()

# 1. Unauthenticated View: Login Form
if not st.session_state["authenticated"]:
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        render_demo_badge("DEMO ENVIRONMENT — AUTHENTICATION HUB")
        st.title("Smart Campus Analytics")
        st.caption("Sign in to access your role-scoped portal")

        with st.form("login_form", clear_on_submit=False):
            username_input = st.text_input("Username / ID", placeholder="e.g. admin, FAC_CSE_01, 21CSE089")
            password_input = st.text_input("Password", type="password", placeholder="Enter your password")
            submitted = st.form_submit_button("Sign In", use_container_width=True)

            if submitted:
                if not username_input or not password_input:
                    st.error("Please provide both username and password.")
                else:
                    user = authenticate_user(username_input.strip(), password_input)
                    if user:
                        st.session_state["authenticated"] = True
                        st.session_state["user"] = user
                        st.rerun()
                    else:
                        st.error("Invalid username or password. Please try again.")

        st.caption("Access is authenticated via salted bcrypt and strictly role-scoped.")

# 2. Authenticated View: Role-based Landing Stubs & Navigation
else:
    user = st.session_state["user"]
    role = user.get("role", "").upper()

    # Sidebar user profile & logout
    with st.sidebar:
        st.subheader("Logged In")
        st.write(f"**{user['name']}**")
        st.caption(f"Role: {role}")
        if user.get("department"):
            st.caption(f"Department: {user['department']}")
        if user.get("mentor_id") and role == "FACULTY":
            st.caption(f"Advisor ID: {user['mentor_id']}")
        st.write("---")
        if st.button("Log Out", use_container_width=True):
            logout()

    # Route by role
    if role == "FACULTY":
        st.title("Faculty Advisory Portal")
        st.info(f"Signed in as advisor {user['name']} ({user['mentor_id']}).")
        st.markdown("""
        ### Next Step
        Please navigate to **1_Faculty_Queue** in the left sidebar to view and manage your prioritized mentee intervention tasks.
        """)

    elif role == "ADMIN":
        st.title("Institution Administration Console")
        st.info(f"Signed in as {user['name']} with global cohort oversight.")
        st.markdown("""
        ### Available Views
        - **1_Faculty_Queue**: View the full institution-wide intervention backlog and triage status across all departments.
        """)

    elif role == "STUDENT":
        st.title("Student Growth Portal")
        st.info(f"Welcome, {user['name']} (Roll ID: {user['student_id']}).")
        st.markdown("""
        Your personalized academic indicators and growth milestones are scoped strictly to your account.
        Student profile details will become active in Phase 4 Part 3.
        """)

    else:
        st.error("Unrecognized user role. Please log out and sign in with valid credentials.")
