"""Verify student portal language and strict student-ID scoping."""

import re
import sys
from pathlib import Path

import pandas as pd
from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from core.auth import DEMO_PASSWORDS, authenticate_user
from core.score import get_student_portal_data, score_student_portal_scenario


def verify() -> None:
    user = authenticate_user("21CSE089", DEMO_PASSWORDS["21CSE089"])
    assert user is not None, "21CSE089 sign-in record is missing."

    app = AppTest.from_file(str(ROOT / "pages" / "6_Student_Portal.py"))
    app.session_state["authenticated"] = True
    app.session_state["user"] = user
    app.run()
    assert not app.exception, app.exception

    visible_parts = []
    for element_type in ("title", "header", "subheader", "markdown", "caption", "text", "metric", "info", "error"):
        for element in app.get(element_type):
            value = str(element.value)
            if "<style" not in value.lower() and "<script" not in value.lower():
                visible_parts.append(value)
    for table in app.dataframe:
        if isinstance(table.value, pd.DataFrame):
            visible_parts.append(table.value.to_string(index=False))
    visible_output = "\n".join(visible_parts)

    banned_words = re.compile(
        r"\b(?:risk|at-risk|rank|priority|segment|triage score|early warning)\b",
        re.IGNORECASE,
    )
    matches = sorted({match.group(0).lower() for match in banned_words.finditer(visible_output)})
    assert not matches, f"Student-facing output contains prohibited terms: {matches}"

    print("=== RAW 21CSE089 PORTAL OUTPUT ===")
    print(visible_output)

    print("\n=== RAW SUBJECT TABLE ===")
    portal_data = get_student_portal_data("21CSE089", user)
    expected_gap = portal_data["student"]["success_score"] - portal_data["cohort_average_score"]
    assert abs(portal_data["score_vs_cohort_average"] - expected_gap) < 0.1
    print(portal_data["subject_marks"].to_string(index=False))
    print("\n=== RAW NEXT STEPS ===")
    print(portal_data["next_steps"].to_string(index=False))

    print("\n=== CROSS-STUDENT ACCESS CHECK ===")
    try:
        get_student_portal_data("21MECH012", user)
    except PermissionError as exc:
        print(f"21CSE089 -> 21MECH012: REFUSED ({type(exc).__name__}: {exc})")
    else:
        raise AssertionError("21CSE089 was able to request 21MECH012's data.")

    scenario = {
        "attendance_pct": portal_data["student"]["attendance_pct"],
        "coding": portal_data["student"]["coding"],
    }
    try:
        score_student_portal_scenario("21MECH012", user, scenario)
    except PermissionError as exc:
        print(f"21CSE089 -> 21MECH012 scenario: REFUSED ({type(exc).__name__})")
    else:
        raise AssertionError("21CSE089 was able to simulate 21MECH012's data.")

    staff_app = AppTest.from_file(str(ROOT / "pages" / "6_Student_Portal.py"))
    staff_app.session_state["authenticated"] = True
    staff_app.session_state["user"] = {"username": "admin", "role": "ADMIN"}
    staff_app.run()
    assert not staff_app.exception, staff_app.exception
    assert staff_app.error
    print("ADMIN page access: REFUSED")

    print("\nStudent portal verification passed.")


if __name__ == "__main__":
    verify()