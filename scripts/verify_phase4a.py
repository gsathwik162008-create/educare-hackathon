"""
Smart Campus Analytics - Phase 4a Verification Script
Validates authentication, bcrypt password hashing, users.csv generation,
and strict role-based data scoping for ADMIN, FACULTY, and STUDENT users.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import sqlite3
import pandas as pd
from core.config import DB_PATH, USERS_CSV_PATH
from core.auth import (
    generate_users_csv,
    authenticate_user,
    get_students_for_user,
    get_interventions_for_user,
    DEMO_PASSWORDS
)

def verify():
    print("=" * 80)
    print("SMART CAMPUS ANALYTICS - PHASE 4A VERIFICATION (AUTH & ROLE SCOPING)")
    print("=" * 80)

    conn = sqlite3.connect(DB_PATH)

    # 1. Generate users.csv and verify structure
    print("\n[1] GENERATING USERS.CSV AND VERIFYING TABLE...")
    users_df = generate_users_csv(conn)
    total_users = len(users_df)
    admin_count = (users_df["role"] == "ADMIN").sum()
    faculty_count = (users_df["role"] == "FACULTY").sum()
    student_count = (users_df["role"] == "STUDENT").sum()

    print(f"   Users generated in users.csv: {total_users}")
    print(f"   Role distribution: ADMIN={admin_count}, FACULTY={faculty_count}, STUDENT={student_count}")
    print("\n   Sample rows from users.csv:")
    display_cols = ["username", "role", "name", "mentor_id", "student_id"]
    print(users_df.head(6)[display_cols].to_string(index=False))

    # Strict structural asserts
    assert admin_count == 1, f"Expected exactly 1 ADMIN, found {admin_count}"
    assert faculty_count == 16, f"Expected exactly 16 FACULTY, found {faculty_count}"
    assert student_count == 600, f"Expected exactly 600 STUDENTS, found {student_count}"
    assert total_users == 617, f"Expected total 617 users, found {total_users}"

    # 2. Test Bcrypt Authentication on Demo Accounts
    print("\n[2] TESTING BCRYPT AUTHENTICATION ON DEMO ACCOUNTS...")
    
    # Test Admin
    admin_user = authenticate_user("admin", DEMO_PASSWORDS["admin"], conn)
    assert admin_user is not None, "Admin authentication failed!"
    assert admin_user["role"] == "ADMIN"
    print(f"   Admin auth: SUCCESS (role: {admin_user['role']})")

    # Test wrong password fails
    bad_auth = authenticate_user("admin", "WrongPassword123!", conn)
    assert bad_auth is None, "Authentication should have failed with wrong password!"
    print("   Admin auth rejection with invalid password: SUCCESS")

    # Test 3 Faculty with known demo passwords
    for f_id in ["FAC_CSE_01", "FAC_MECH_01", "FAC_CIVIL_01"]:
        f_user = authenticate_user(f_id, DEMO_PASSWORDS[f_id], conn)
        assert f_user is not None, f"Faculty {f_id} authentication failed!"
        assert f_user["role"] == "FACULTY"
        assert f_user["mentor_id"] == f_id
        print(f"   Faculty {f_id} auth: SUCCESS (mentor_id: {f_user['mentor_id']})")

    # Test Engineered Students
    for s_id in ["21CSE089", "22ECE045", "21MECH012", "23CIVIL034", "22EEE071"]:
        s_user = authenticate_user(s_id, DEMO_PASSWORDS[s_id], conn)
        assert s_user is not None, f"Student {s_id} authentication failed!"
        assert s_user["role"] == "STUDENT"
        assert s_user["student_id"] == s_id
        print(f"   Student {s_id} auth: SUCCESS (student_id: {s_user['student_id']})")

    # 3. Test Scoping: Admin Sees All 600 Records
    print("\n[3] TESTING ADMIN DATA SCOPING...")
    admin_students = get_students_for_user(admin_user, conn=conn)
    admin_interventions = get_interventions_for_user(admin_user, conn=conn)
    print(f"   ADMIN visibility: {len(admin_students)} students, {len(admin_interventions)} interventions")
    assert len(admin_students) == 600, f"ADMIN must see exactly 600 students, saw {len(admin_students)}"
    assert len(admin_interventions) >= 100, "ADMIN must see all interventions"

    # 4. Test Scoping: Faculty Scoping & Isolation
    print("\n[4] TESTING FACULTY DATA SCOPING & CROSS-MENTOR ISOLATION...")
    fac_cse = authenticate_user("FAC_CSE_01", DEMO_PASSWORDS["FAC_CSE_01"], conn)
    fac_mech = authenticate_user("FAC_MECH_01", DEMO_PASSWORDS["FAC_MECH_01"], conn)
    
    cse_students = get_students_for_user(fac_cse, conn=conn)
    mech_students = get_students_for_user(fac_mech, conn=conn)
    print(f"   FAC_CSE_01 visible students: {len(cse_students)}")
    print(f"   FAC_MECH_01 visible students: {len(mech_students)}")

    # Assert all returned students belong to this mentor
    assert (cse_students["mentor_id"] == "FAC_CSE_01").all(), "FAC_CSE_01 saw a student with another mentor!"
    assert (mech_students["mentor_id"] == "FAC_MECH_01").all(), "FAC_MECH_01 saw a student with another mentor!"

    # Assert cross-mentor access violation is impossible
    assert "21MECH012" not in cse_students["student_id"].values, "CROSS-MENTOR BREACH: FAC_CSE_01 can see FAC_MECH_01 student 21MECH012!"
    assert "21CSE089" not in mech_students["student_id"].values, "CROSS-MENTOR BREACH: FAC_MECH_01 can see FAC_CSE_01 student 21CSE089!"
    print("   CROSS-MENTOR ISOLATION VERIFIED: Faculty cannot access students outside their assigned mentorship.")

    # 5. Test Scoping: Student Scoping & Peer Isolation
    print("\n[5] TESTING STUDENT DATA SCOPING & PEER ISOLATION...")
    aarav_user = authenticate_user("21CSE089", DEMO_PASSWORDS["21CSE089"], conn)
    rahul_user = authenticate_user("21MECH012", DEMO_PASSWORDS["21MECH012"], conn)

    aarav_data = get_students_for_user(aarav_user, conn=conn)
    rahul_data = get_students_for_user(rahul_user, conn=conn)
    print(f"   21CSE089 (Aarav) visible records: {len(aarav_data)} (ID: {aarav_data.iloc[0]['student_id']})")
    print(f"   21MECH012 (Rahul) visible records: {len(rahul_data)} (ID: {rahul_data.iloc[0]['student_id']})")

    assert len(aarav_data) == 1, f"Student must only see 1 record, saw {len(aarav_data)}"
    assert aarav_data.iloc[0]["student_id"] == "21CSE089"
    assert len(rahul_data) == 1, f"Student must only see 1 record, saw {len(rahul_data)}"
    assert rahul_data.iloc[0]["student_id"] == "21MECH012"

    # Assert student peer breach is impossible
    assert "21MECH012" not in aarav_data["student_id"].values, "PEER BREACH: Aarav can see Rahul's record!"
    assert "21CSE089" not in rahul_data["student_id"].values, "PEER BREACH: Rahul can see Aarav's record!"
    print("   PEER ISOLATION VERIFIED: Student can only view their own record.")

    # 6. FAC_GEN_01 Inspection
    print("\n[6] INSPECTING FAC_GEN_01 ASSIGNMENTS...")
    fac_gen = {"username": "FAC_GEN_01", "role": "FACULTY", "mentor_id": "FAC_GEN_01"}
    gen_students = get_students_for_user(fac_gen, conn=conn)
    print(f"   FAC_GEN_01 mentors {len(gen_students)} students across departments:")
    dept_dist = gen_students["department"].value_counts().to_dict()
    for d, cnt in dept_dist.items():
        print(f"     - {d}: {cnt} students")

    conn.close()
    print("\n" + "=" * 80)
    print("PHASE 4A ALL STRICT ASSERTIONS VERIFIED AND PASSED LOUDLY")
    print("=" * 80)

if __name__ == "__main__":
    verify()
