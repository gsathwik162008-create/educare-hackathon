"""
Smart Campus Analytics - Phase 4b Verification Script
Tests login and strict data scoping enforcement:
1. Log in as FAC_CSE_01.
2. Attempt to load a student belonging to FAC_MECH_01 (e.g. 21MECH012) via get_student_by_id_scoped().
3. Assert that access is refused with PermissionError.
4. Verify FAC_CSE_01 can load their own student (21CSE089) without error.
5. Verify ADMIN can load both.
6. Verify STUDENT (21CSE089) cannot load peer (21MECH012).
7. Print raw output and verification steps.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.auth import (
    authenticate_user,
    get_student_by_id_scoped,
    DEMO_PASSWORDS
)

def verify():
    print("=" * 80)
    print("SMART CAMPUS ANALYTICS - PHASE 4B VERIFICATION (SCOPING REFUSAL TESTS)")
    print("=" * 80)

    # 1. Authenticate as FAC_CSE_01
    print("\n[1] AUTHENTICATING AS FAC_CSE_01...")
    fac_cse = authenticate_user("FAC_CSE_01", DEMO_PASSWORDS["FAC_CSE_01"])
    assert fac_cse is not None, "FAC_CSE_01 authentication failed!"
    print(f"   Logged in as: {fac_cse['name']} ({fac_cse['username']}, Role: {fac_cse['role']})")

    # 2. Attempt to load own student (21CSE089)
    print("\n[2] LOADING PERMITTED STUDENT (21CSE089) UNDER FAC_CSE_01 SCOPE...")
    own_student = get_student_by_id_scoped("21CSE089", fac_cse)
    print(f"   SUCCESS: Loaded {own_student['name']} ({own_student['student_id']}), Mentor: {own_student['mentor_id']}")
    assert own_student["student_id"] == "21CSE089"
    assert own_student["mentor_id"] == "FAC_CSE_01"

    # 3. Attempt to load FAC_MECH_01 student (21MECH012) - MUST BE REFUSED
    print("\n[3] ATTEMPTING CROSS-MENTOR ACCESS: FAC_CSE_01 TRYING TO LOAD 21MECH012...")
    refusal_caught = False
    refusal_message = ""
    try:
        get_student_by_id_scoped("21MECH012", fac_cse)
    except PermissionError as e:
        refusal_caught = True
        refusal_message = str(e)
        print(f"   REFUSAL CONFIRMED: Caught expected PermissionError:")
        print(f"   >>> {refusal_message}")

    assert refusal_caught, "SECURITY FAILURE: FAC_CSE_01 was able to load student 21MECH012 without PermissionError!"
    print("   ASSERTION PASSED: Cross-mentor access strictly blocked.")

    # 4. Attempt to load FAC_CIVIL_01 student (23CIVIL034) - MUST BE REFUSED
    print("\n[4] ATTEMPTING CROSS-MENTOR ACCESS: FAC_CSE_01 TRYING TO LOAD 23CIVIL034...")
    refusal_caught_civil = False
    try:
        get_student_by_id_scoped("23CIVIL034", fac_cse)
    except PermissionError as e:
        refusal_caught_civil = True
        print(f"   REFUSAL CONFIRMED: {e}")

    assert refusal_caught_civil, "SECURITY FAILURE: FAC_CSE_01 was able to load student 23CIVIL034!"
    print("   ASSERTION PASSED: Cross-department access strictly blocked.")

    # 5. Verify Student Peer-to-Peer Access Refusal
    print("\n[5] ATTEMPTING PEER-TO-PEER ACCESS: STUDENT 21CSE089 TRYING TO LOAD 21MECH012...")
    student_user = authenticate_user("21CSE089", DEMO_PASSWORDS["21CSE089"])
    peer_refusal_caught = False
    try:
        get_student_by_id_scoped("21MECH012", student_user)
    except PermissionError as e:
        peer_refusal_caught = True
        print(f"   REFUSAL CONFIRMED: {e}")

    assert peer_refusal_caught, "SECURITY FAILURE: Student was able to access peer record!"
    print("   ASSERTION PASSED: Peer student access strictly blocked.")

    # 6. Verify Admin Can Load Both
    print("\n[6] VERIFYING ADMIN ACCESS TO ALL STUDENTS...")
    admin_user = authenticate_user("admin", DEMO_PASSWORDS["admin"])
    cse_by_admin = get_student_by_id_scoped("21CSE089", admin_user)
    mech_by_admin = get_student_by_id_scoped("21MECH012", admin_user)
    print(f"   ADMIN successfully loaded: {cse_by_admin['student_id']} ({cse_by_admin['name']})")
    print(f"   ADMIN successfully loaded: {mech_by_admin['student_id']} ({mech_by_admin['name']})")
    assert cse_by_admin["student_id"] == "21CSE089"
    assert mech_by_admin["student_id"] == "21MECH012"
    print("   ASSERTION PASSED: Admin has full global visibility.")

    # 7. Test Intervention Status Scoping: FAC_CSE_01 tries to update 21MECH012 intervention
    print("\n[7] TESTING INTERVENTION STATUS UPDATE SCOPE ENFORCEMENT...")
    import sqlite3
    from core.config import DB_PATH, DEMO_TODAY
    from core.interventions import update_intervention_status

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Find an intervention belonging to 21MECH012 (mentored by FAC_MECH_01)
    mech_int = cursor.execute(
        "SELECT id, student_id, action, status FROM interventions WHERE student_id = '21MECH012' LIMIT 1"
    ).fetchone()
    assert mech_int is not None, "No intervention record found for 21MECH012!"
    target_int_id, target_sid, target_act, orig_status = mech_int
    print(f"   Target Intervention ID #{target_int_id} (Student: {target_sid}, Action: '{target_act}', Current Status: '{orig_status}')")

    attempted_status = "done" if orig_status != "done" else "in progress"
    int_refusal_caught = False
    try:
        update_intervention_status(target_int_id, attempted_status, user=fac_cse, conn=conn)
    except PermissionError as pe:
        int_refusal_caught = True
        print(f"   REFUSAL CONFIRMED: Caught expected PermissionError for FAC_CSE_01 on 21MECH012 intervention:")
        print(f"   >>> {pe}")

    assert int_refusal_caught, "SECURITY FAILURE: FAC_CSE_01 was able to update 21MECH012 intervention!"

    # Verify database status is unchanged
    status_in_db = cursor.execute("SELECT status FROM interventions WHERE id = ?", (target_int_id,)).fetchone()[0]
    print(f"   DB Verification: Status before = '{orig_status}', Status in DB now = '{status_in_db}'")
    assert status_in_db == orig_status, f"DATABASE CORRUPTION: Status changed to {status_in_db} despite refusal!"
    print("   ASSERTION PASSED: DB status remains unchanged.")

    # STUDENT role attempt to update own intervention should also be refused
    student_int_refusal_caught = False
    try:
        cse_int_id = cursor.execute(
            "SELECT id FROM interventions WHERE student_id = '21CSE089' LIMIT 1"
        ).fetchone()[0]
        update_intervention_status(cse_int_id, "done", user=student_user, conn=conn)
    except PermissionError as pe:
        student_int_refusal_caught = True
        print(f"   REFUSAL CONFIRMED: Student attempt to update intervention refused with: {pe}")
    assert student_int_refusal_caught, "SECURITY FAILURE: Student was able to update intervention status!"

    # 8. Verify Due Dates Relative to DEMO_TODAY
    print("\n[8] VERIFYING INTERVENTION DUE DATES RELATIVE TO DEMO_TODAY...")
    print(f"   DEMO_TODAY constant in config.py: {DEMO_TODAY}")
    due_dates = [r[0] for r in cursor.execute("SELECT due_date FROM interventions LIMIT 10").fetchall()]
    print(f"   Sample due dates in DB: {due_dates[:5]}")
    # All due dates should be >= DEMO_TODAY
    for dd in due_dates:
        assert dd >= DEMO_TODAY, f"Due date {dd} is before DEMO_TODAY {DEMO_TODAY}!"
    print("   ASSERTION PASSED: Intervention due dates are properly positioned relative to DEMO_TODAY.")

    conn.close()

    print("\n" + "=" * 80)
    print("PHASE 4B SCOPING REFUSAL TESTS ALL PASSED SUCCESSFULLY")
    print("=" * 80)

if __name__ == "__main__":
    verify()
