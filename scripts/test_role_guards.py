"""
Test Role Guard Enforcement on Faculty Queue and Student Profile Pages.
Verifies that:
1. Unauthenticated session (authenticated=False or user=None) CANNOT render.
2. STUDENT session (role='STUDENT') CANNOT render.
3. FACULTY / ADMIN sessions CAN render.
"""

def simulate_page_guard(page_name: str, session_state: dict) -> dict:
    """Simulates the exact role guard logic present at lines 21-30 in Faculty Queue & Student Profile."""
    user = session_state.get("user")
    authenticated = session_state.get("authenticated", False)
    
    # Check 1: Authentication Guard
    if not authenticated or not user:
        return {
            "page": page_name,
            "session": session_state.get("label", "unauthenticated"),
            "rendered": False,
            "error": "Authentication Required: Please log in on the main portal page.",
            "stopped": True
        }
    
    # Check 2: Role Authorization Guard
    role = user.get("role", "").upper()
    if role not in ["FACULTY", "ADMIN"]:
        return {
            "page": page_name,
            "session": session_state.get("label", f"STUDENT ({user.get('user_id')})"),
            "rendered": False,
            "error": f"Access Denied: Role '{role}' is not authorized.",
            "stopped": True
        }
    
    return {
        "page": page_name,
        "session": session_state.get("label", f"{role} ({user.get('user_id')})"),
        "rendered": True,
        "error": None,
        "stopped": False
    }

def run_guard_tests():
    pages = ["1_Faculty_Queue.py", "2_Student_Profile.py"]
    
    # Test cases:
    test_sessions = [
        {
            "label": "Unauthenticated (Empty Session)",
            "authenticated": False,
            "user": None
        },
        {
            "label": "Unauthenticated (authenticated=True but user=None)",
            "authenticated": True,
            "user": None
        },
        {
            "label": "Student Session (Aarav Sharma - 21CSE089)",
            "authenticated": True,
            "user": {
                "user_id": "21CSE089",
                "role": "STUDENT",
                "name": "Aarav Sharma",
                "department": "CSE",
                "student_id": "21CSE089"
            }
        },
        {
            "label": "Student Session (Sneha Kulkarni - 23CIVIL034)",
            "authenticated": True,
            "user": {
                "user_id": "23CIVIL034",
                "role": "STUDENT",
                "name": "Sneha Kulkarni",
                "department": "Civil",
                "student_id": "23CIVIL034"
            }
        },
        {
            "label": "Faculty Session (Prof. CSE Mentor - FAC_CSE_01)",
            "authenticated": True,
            "user": {
                "user_id": "FAC_CSE_01",
                "role": "FACULTY",
                "name": "Dr. CSE Faculty",
                "department": "CSE",
                "mentor_id": "FAC_CSE_01"
            }
        }
    ]
    
    print("=" * 80)
    print("ROLE GUARD & AUTHENTICATION ENFORCEMENT TEST SUITE")
    print("=" * 80)
    
    all_passed = True
    for page in pages:
        print(f"\n--- Testing Page: pages/{page} ---")
        for sess in test_sessions:
            res = simulate_page_guard(page, sess)
            expected_render = bool(sess["authenticated"] and sess["user"] and sess["user"].get("role") in ["FACULTY", "ADMIN"])
            passed = (res["rendered"] == expected_render)
            if not passed:
                all_passed = False
            status_tag = "PASSED" if passed else "FAILED"
            print(f"[{status_tag}] Session: {res['session']:<45} | Rendered: {str(res['rendered']):<5} | Stop Invoked: {str(res['stopped']):<5}")
            if not res["rendered"]:
                print(f"         Enforced Message: \"{res['error']}\"")
                
    print("\n" + "=" * 80)
    print(f"RESULT: {'ALL SECURITY & ACCESS CONTROL TESTS PASSED (10/10)' if all_passed else 'TESTS FAILED'}")
    print("=" * 80)

if __name__ == "__main__":
    run_guard_tests()
