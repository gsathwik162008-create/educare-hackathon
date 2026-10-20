"""
Smart Campus Analytics - Main Entry Point & Authentication Hub
Handles user login, bcrypt authentication, session state management,
and role-based routing for ADMIN, FACULTY, and STUDENT users.
"""

import streamlit as st
import pandas as pd
from core.auth import authenticate_user

# Streamlit Page Config
st.set_page_config(
    page_title="Smart Campus Analytics | Login",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for rich aesthetics
st.markdown("""
<style>
    .login-card {
        background: rgba(255, 255, 255, 0.05);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 12px;
        padding: 30px;
        backdrop-filter: blur(10px);
        max-width: 480px;
        margin: 40px auto;
        box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.37);
    }
    .main-title {
        font-family: 'Inter', sans-serif;
        font-weight: 700;
        font-size: 2.2rem;
        background: linear-gradient(135deg, #60A5FA 0%, #A78BFA 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        text-align: center;
        margin-bottom: 8px;
    }
    .sub-title {
        color: #94A3B8;
        font-size: 0.95rem;
        text-align: center;
        margin-bottom: 24px;
    }
    .user-badge {
        display: inline-block;
        padding: 4px 12px;
        border-radius: 16px;
        font-size: 0.85rem;
        font-weight: 600;
        background: #1E293B;
        color: #38BDF8;
        border: 1px solid #0284C7;
    }
</style>
""", unsafe_allow_html=True)

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
        st.markdown('<div class="main-title">Smart Campus Analytics</div>', unsafe_allow_html=True)
        st.markdown('<div class="sub-title">Sign in to access your role-scoped portal</div>', unsafe_allow_html=True)

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
                        st.success(f"Welcome back, {user['name']}!")
                        st.rerun()
                    else:
                        st.error("Invalid username or password. Please try again.")

        st.caption("🔒 All access is protected by salted bcrypt encryption and role scoping.")

# 2. Authenticated View: Role-based Landing Stubs & Navigation
else:
    user = st.session_state["user"]
    role = user.get("role", "").upper()

    # Sidebar user profile & logout
    with st.sidebar:
        st.markdown(f"### 👤 Logged In As")
        st.markdown(f"**{user['name']}**")
        st.markdown(f'<span class="user-badge">{role}</span>', unsafe_allow_html=True)
        if user.get("department"):
            st.caption(f"Department: {user['department']}")
        if user.get("mentor_id") and role == "FACULTY":
            st.caption(f"Advisor ID: {user['mentor_id']}")
        st.write("---")
        if st.button("🚪 Log Out", use_container_width=True):
            logout()

    # Route by role
    if role == "FACULTY":
        st.markdown(f"## 🏛️ Faculty Advisory Portal")
        st.info(f"Signed in as advisor **{user['name']}** ({user['mentor_id']}).")
        st.markdown("""
        ### Next Step
        Please navigate to **`1_Faculty_Queue`** in the left sidebar to view and manage your prioritized mentee intervention tasks.
        """)

    elif role == "ADMIN":
        st.markdown(f"## ⚙️ Institution Administration Console")
        st.success(f"Signed in as **{user['name']}** with global cohort oversight.")
        st.markdown("""
        ### Available Views
        - **`1_Faculty_Queue`**: View the full institution-wide intervention backlog and triage status across all departments.
        """)

    elif role == "STUDENT":
        st.markdown(f"## 🎓 Student Growth Portal")
        st.success(f"Welcome, **{user['name']}** (Roll No: `{user['student_id']}`).")
        st.markdown("""
        Your personalized academic indicators and growth milestones are scoped strictly to your account.
        Student profile details will become active in Phase 4 Part 3.
        """)

    else:
        st.error("Unrecognized user role. Please log out and sign in with valid credentials.")
