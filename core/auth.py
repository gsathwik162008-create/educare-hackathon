"""
Smart Campus Analytics - Authentication & Role Scoping Module
Implements user creation, password hashing with bcrypt, credentials validation,
and role-based data access scoping for ADMIN, FACULTY, and STUDENT users.
"""

import bcrypt
import sqlite3
import pandas as pd
from pathlib import Path
from core.config import DB_PATH, USERS_CSV_PATH

# Demo user credentials passwords
DEMO_PASSWORDS = {
    # 1. Admin
    "admin": "Admin@2026",
    
    # 2. 3 Faculty with known demo passwords
    "FAC_CSE_01": "Faculty@CSE1",
    "FAC_MECH_01": "Faculty@MECH1",
    "FAC_CIVIL_01": "Faculty@CIVIL1",
    
    # 3. 8 Engineered students (5 at-risk, 3 stars)
    "21CSE089": "Student@21CSE089",
    "22ECE045": "Student@22ECE045",
    "21MECH012": "Student@21MECH012",
    "23CIVIL034": "Student@23CIVIL034",
    "22EEE071": "Student@22EEE071",
    "21CSE001": "Student@21CSE001",
    "22ECE005": "Student@22ECE005",
    "21MECH003": "Student@21MECH003",
}

DEFAULT_FACULTY_PASSWORD = "Faculty@Pass2026"
DEFAULT_STUDENT_PASSWORD = "Student@Pass2026"

def hash_password(plain_password: str) -> str:
    """Hash a plaintext password using bcrypt with salt."""
    salt = bcrypt.gensalt(rounds=6)
    hashed = bcrypt.hashpw(plain_password.encode("utf-8"), salt)
    return hashed.decode("utf-8")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plaintext password against a bcrypt hash."""
    try:
        return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
    except Exception:
        return False

def generate_users_csv(conn=None) -> pd.DataFrame:
    """
    Generate data/users.csv containing:
    - 1 ADMIN
    - 1 FACULTY per unique mentor_id in students_unified (16 faculty)
    - 1 STUDENT per student_id in students_unified (600 students)
    All passwords are saved as bcrypt hashes.
    """
    close_at_end = False
    if conn is None:
        conn = sqlite3.connect(DB_PATH)
        close_at_end = True

    # 1. Fetch unique mentors
    mentors_df = pd.read_sql("SELECT DISTINCT mentor_id FROM students_unified ORDER BY mentor_id", conn)
    # 2. Fetch all students
    students_df = pd.read_sql("SELECT student_id, name, department, mentor_id FROM students_unified ORDER BY student_id", conn)

    user_records = []

    # Admin record
    admin_hash = hash_password(DEMO_PASSWORDS["admin"])
    user_records.append({
        "username": "admin",
        "role": "ADMIN",
        "name": "System Administrator",
        "password_hash": admin_hash,
        "mentor_id": "",
        "student_id": "",
        "department": ""
    })

    # Faculty records (16 unique mentor_ids)
    for _, row in mentors_df.iterrows():
        mid = row["mentor_id"]
        pwd = DEMO_PASSWORDS.get(mid, DEFAULT_FACULTY_PASSWORD)
        pwd_hash = hash_password(pwd)
        user_records.append({
            "username": mid,
            "role": "FACULTY",
            "name": f"Faculty Advisor ({mid})",
            "password_hash": pwd_hash,
            "mentor_id": mid,
            "student_id": "",
            "department": mid.split("_")[1] if len(mid.split("_")) > 1 else ""
        })

    # Student records (600 students)
    for _, row in students_df.iterrows():
        sid = row["student_id"]
        pwd = DEMO_PASSWORDS.get(sid, DEFAULT_STUDENT_PASSWORD)
        pwd_hash = hash_password(pwd)
        user_records.append({
            "username": sid,
            "role": "STUDENT",
            "name": row["name"],
            "password_hash": pwd_hash,
            "mentor_id": row["mentor_id"],
            "student_id": sid,
            "department": row["department"]
        })

    users_df = pd.DataFrame(user_records)
    USERS_CSV_PATH.parent.mkdir(parents=True, exist_ok=True)
    users_df.to_csv(USERS_CSV_PATH, index=False)

    # Also store in SQLite for fast query joining
    users_df.to_sql("users", conn, if_exists="replace", index=False)

    if close_at_end:
        conn.close()

    return users_df

def authenticate_user(username: str, plain_password: str, conn=None) -> dict:
    """
    Authenticate a user by username and password.
    Returns user dict with role scoping attributes if successful, or None if invalid.
    """
    close_at_end = False
    if conn is None:
        conn = sqlite3.connect(DB_PATH)
        close_at_end = True

    cursor = conn.cursor()
    row = cursor.execute("SELECT username, role, name, password_hash, mentor_id, student_id, department FROM users WHERE username = ?", (username,)).fetchone()
    
    if close_at_end:
        conn.close()

    if not row:
        return None

    u_name, role, full_name, pwd_hash, mentor_id, student_id, dept = row
    if verify_password(plain_password, pwd_hash):
        return {
            "username": u_name,
            "role": role,
            "name": full_name,
            "mentor_id": mentor_id,
            "student_id": student_id,
            "department": dept
        }
    return None

def get_students_for_user(user: dict, table_name: str = "students_scored", conn=None) -> pd.DataFrame:
    """
    Core role-based scoping engine:
    - ADMIN: all records (600 rows)
    - FACULTY: only students with student.mentor_id == user.mentor_id
    - STUDENT: only own record with student.student_id == user.student_id
    - Others / Invalid: empty DataFrame
    """
    close_at_end = False
    if conn is None:
        conn = sqlite3.connect(DB_PATH)
        close_at_end = True

    role = user.get("role", "").upper()
    if role == "ADMIN":
        df = pd.read_sql(f"SELECT * FROM {table_name}", conn)
    elif role == "FACULTY":
        mid = user.get("mentor_id") or user.get("username")
        query = f"SELECT * FROM {table_name} WHERE mentor_id = ?"
        df = pd.read_sql(query, conn, params=(mid,))
    elif role == "STUDENT":
        sid = user.get("student_id") or user.get("username")
        query = f"SELECT * FROM {table_name} WHERE student_id = ?"
        df = pd.read_sql(query, conn, params=(sid,))
    else:
        df = pd.DataFrame()

    if close_at_end:
        conn.close()

    return df

def get_interventions_for_user(user: dict, conn=None) -> pd.DataFrame:
    """
    Role-based scoping for the interventions table:
    - ADMIN: all interventions
    - FACULTY: only interventions where student belongs to user.mentor_id or assigned_to == user.mentor_id
    - STUDENT: only interventions for student_id == user.student_id
    """
    close_at_end = False
    if conn is None:
        conn = sqlite3.connect(DB_PATH)
        close_at_end = True

    role = user.get("role", "").upper()
    if role == "ADMIN":
        df = pd.read_sql("SELECT * FROM interventions", conn)
    elif role == "FACULTY":
        mid = user.get("mentor_id") or user.get("username")
        query = """
        SELECT i.* FROM interventions i
        JOIN students_unified su ON i.student_id = su.student_id
        WHERE su.mentor_id = ? OR i.assigned_to = ?
        """
        df = pd.read_sql(query, conn, params=(mid, mid))
    elif role == "STUDENT":
        sid = user.get("student_id") or user.get("username")
        query = "SELECT * FROM interventions WHERE student_id = ?"
        df = pd.read_sql(query, conn, params=(sid,))
    else:
        df = pd.DataFrame()

    if close_at_end:
        conn.close()

    return df

def get_student_by_id_scoped(student_id: str, user: dict, conn=None) -> dict:
    """
    Load a single student record with strict role-based access verification:
    - If user has no permission to view student_id, raises PermissionError.
    - Returns student record dict if permitted, or raises ValueError if not found.
    """
    close_at_end = False
    if conn is None:
        conn = sqlite3.connect(DB_PATH)
        close_at_end = True

    role = user.get("role", "").upper()
    sid = str(student_id).strip().upper()

    if role == "ADMIN":
        query = "SELECT * FROM students_scored WHERE student_id = ?"
        row = pd.read_sql(query, conn, params=(sid,))
    elif role == "FACULTY":
        mid = user.get("mentor_id") or user.get("username")
        query = "SELECT * FROM students_scored WHERE student_id = ? AND mentor_id = ?"
        row = pd.read_sql(query, conn, params=(sid, mid))
    elif role == "STUDENT":
        own_id = user.get("student_id") or user.get("username")
        if sid != own_id:
            if close_at_end:
                conn.close()
            raise PermissionError(f"Access Denied: Student '{own_id}' cannot access peer record '{sid}'.")
        query = "SELECT * FROM students_scored WHERE student_id = ?"
        row = pd.read_sql(query, conn, params=(sid,))
    else:
        if close_at_end:
            conn.close()
        raise PermissionError("Access Denied: Unrecognized or missing user role.")

    if close_at_end:
        conn.close()

    if row.empty:
        # Check if student exists in database to distinguish between 404 Not Found vs 403 Forbidden
        chk_conn = sqlite3.connect(DB_PATH)
        exists = chk_conn.cursor().execute("SELECT COUNT(*) FROM students_scored WHERE student_id = ?", (sid,)).fetchone()[0] > 0
        chk_conn.close()
        if exists:
            raise PermissionError(f"Access Denied: User '{user.get('username')}' (Role: {role}) does not have permission to view student '{sid}'.")
        else:
            raise ValueError(f"Student ID '{sid}' not found in database.")

    return row.iloc[0].to_dict()

