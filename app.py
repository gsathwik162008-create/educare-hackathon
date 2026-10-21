"""
Smart Campus Analytics - Authentication Hub & Entry Point
Handles login, then dynamically controls allowed navigation via st.navigation.
Before login: only login page, no side navigation.
After login: role-allowed pages with 'Home' as root page.
"""

import streamlit as st
from core.auth import authenticate_user
from core.ui import load_css, render_demo_badge

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

# Unauthenticated Login View Definition
def login_page():
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

# Configure navigation based on authentication status and role
if not st.session_state.get("authenticated"):
    # Before login: Show only the Login page, no pages allowed
    pg = st.navigation([st.Page(login_page, title="Sign In", icon=None)])
    pg.run()
else:
    user = st.session_state["user"]
    role = user.get("role", "").upper()

    # Define role-allowed pages
    home_p = st.Page("pages/home_page.py", title="Home", icon=None, default=True)
    queue_p = st.Page("pages/1_Faculty_Queue.py", title="Faculty Queue", icon=None)
    profile_p = st.Page("pages/2_Student_Profile.py", title="Student Profile", icon=None)
    cohort_p = st.Page("pages/3_Cohort_Overview.py", title="Cohort Overview", icon=None)
    trends_p = st.Page("pages/4_Trends.py", title="Trends", icon=None)

    if role == "ADMIN":
        allowed_pages = [home_p, queue_p, profile_p, cohort_p, trends_p]
    elif role == "FACULTY":
        allowed_pages = [home_p, queue_p, profile_p, trends_p]
    elif role == "STUDENT":
        allowed_pages = [home_p]
    else:
        allowed_pages = [home_p]

    # Sidebar profile & log out button
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

    pg = st.navigation(allowed_pages)
    pg.run()
