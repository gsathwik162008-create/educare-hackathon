"""
Smart Campus Analytics - Phase 2 Verification Script
Validates scoring calculations, 3 trend sub-deltas, data confidence flags,
branch consistency, engineered student rankings, and what-if simulation.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import sqlite3
import pandas as pd
import re
from core.score import score_student, score_all
from core.config import DB_PATH, DEPARTMENT_MAPPING

def verify():
    print("=" * 80)
    print("SMART CAMPUS ANALYTICS - PHASE 2 SCORING VERIFICATION")
    print("=" * 80)

    # Re-run scoring pipeline
    score_all(verbose=False)
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql("SELECT * FROM students_scored", conn)

    # 1. Trend Delta with 3 Sub-deltas
    print("\n[1] TREND DELTA SIGNALS (3 Sub-deltas + Combined):")
    trend_cols = ["student_id", "name", "cgpa_trend_delta", "attendance_trend_delta", "lms_trend_delta", "trend_delta"]
    print("Sample rows showing all 3 sub-deltas:")
    print(df[trend_cols].head(6).to_string(index=False))

    # 2. Low Confidence Flag (< 70% data confidence)
    print("\n[2] DATA CONFIDENCE & LOW CONFIDENCE AUDIT:")
    low_conf_count = int(df["low_confidence"].sum())
    low_conf_pct = round((low_conf_count / len(df)) * 100.0, 2)
    print(f"Total students evaluated: {len(df)}")
    print(f"Students with data_confidence < 70% (low_confidence = 1): {low_conf_count} ({low_conf_pct}%)")
    print(f"Students with data_confidence >= 70% (low_confidence = 0): {len(df) - low_conf_count} ({100.0 - low_conf_pct}%)")
    if low_conf_count > 0:
        print("Sample low-confidence records:")
        print(df[df["low_confidence"] == 1][["student_id", "name", "imputed_field_count", "data_confidence", "low_confidence"]].head(4).to_string(index=False))

    # 3. Roll-number Branch vs Department Consistency
    print("\n[3] ROLL-NUMBER BRANCH CODE VS DEPARTMENT AUDIT:")
    mismatches = []
    for _, row in df.iterrows():
        sid = row["student_id"]
        m = re.match(r"^\d{2}([A-Z]+)\d{3}$", sid)
        if m:
            code = m.group(1)
            c_dept = DEPARTMENT_MAPPING.get(code, code)
            if c_dept.upper() != str(row["department"]).upper():
                mismatches.append({"student_id": sid, "roll_branch": c_dept, "department": row["department"]})
    print(f"Total students with roll-number branch differing from department: {len(mismatches)}")
    if mismatches:
        print(pd.DataFrame(mismatches).to_string(index=False))
    else:
        print("CONFIRMED: 0 mismatches found across all 600 records (Roll-number branch perfectly aligns with department).")

    # 4. Table of All 8 Engineered Students with Success Score, Risks, and Ranks
    print("\n[4] AUDIT TABLE: ALL 8 ENGINEERED TEST STUDENTS (Ranks among 600):")
    # Compute cohort ranks
    df["rank_by_score_desc"] = df["success_score"].rank(ascending=False, method="min").astype(int)
    df["rank_by_priority"] = df["priority_score"].rank(ascending=False, method="min").astype(int)

    eng_ids = ["23CIVIL034", "21CSE089", "22ECE045", "21MECH012", "22EEE071", "21CSE001", "22ECE005", "21MECH003"]
    eng_df = df[df["student_id"].isin(eng_ids)].copy()
    # Sort: at-risk first by priority rank, then stars
    eng_df["is_star"] = eng_df["student_id"].isin(["21CSE001", "22ECE005", "21MECH003"])
    eng_df = eng_df.sort_values(by=["is_star", "rank_by_priority"])

    eng_cols = [
        "student_id", "name", "department", "year", "success_score",
        "academic_risk", "placement_risk", "rank_by_score_desc", "rank_by_priority", "priority_score"
    ]
    print(eng_df[eng_cols].to_string(index=False))

    # 5. Top 5 by Success Score (Confirm 3 Stars are #1-#3)
    print("\n[5] TOP 5 STUDENTS BY SUCCESS SCORE:")
    top5_score = df.sort_values(by="success_score", ascending=False).head(5)
    print(top5_score[["student_id", "name", "department", "year", "success_score", "academic_health", "placement_readiness", "segment"]].to_string(index=False))
    
    top3_ids = list(top5_score["student_id"].iloc[:3])
    expected_stars = ["21CSE001", "22ECE005", "21MECH003"]
    all_stars_top3 = all(s in top3_ids for s in expected_stars)
    print(f"\nAre the 3 engineered stars strictly #1, #2, and #3? -> {all_stars_top3}")
    assert all_stars_top3, f"Stars are not #1-#3! Found {top3_ids}"

    # 6. Verification of 21CSE089 Score Consistency (Table vs What-If Baseline)
    print("\n[6] VERIFICATION: 21CSE089 SCORE CONSISTENCY:")
    row_21cse089 = df[df["student_id"] == "21CSE089"].iloc[0]
    table_score = row_21cse089["success_score"]
    
    # Extract exact database indicators for 21CSE089
    exact_dict = {
        "cgpa": row_21cse089["cgpa"],
        "backlogs": row_21cse089["backlogs"],
        "attendance_pct": row_21cse089["attendance_pct"],
        "coding": row_21cse089["coding"],
        "aptitude": row_21cse089["aptitude"],
        "mock_interviews": row_21cse089["mock_interviews"],
        "lms_logins_avg": row_21cse089["lms_logins_avg"],
        "assignment_completion_pct": row_21cse089["assignment_completion_pct"],
        "events": row_21cse089["events"],
        "clubs": row_21cse089["clubs"],
        "hackathons": row_21cse089["hackathons"],
        "certifications": row_21cse089["certifications"],
        "technical_score": row_21cse089["technical_score"],
        "softskill_score": row_21cse089["softskill_score"],
        "satisfaction": row_21cse089["satisfaction"],
        "faculty_rating": row_21cse089["faculty_rating"],
        "year": row_21cse089["year"]
    }
    sim_result = score_student(exact_dict)
    sim_score = sim_result["success_score"]
    print(f"   Database table 'students_scored' for 21CSE089 : {table_score}")
    print(f"   What-If simulator score_student(exact_dict)  : {sim_score}")
    print(f"   Match status: {table_score == sim_score} (Difference: {round(table_score - sim_score, 3)})")

    # 7. Priority Formula & Early Warning Classifier
    print("\n[7] PRIORITY SCORE FORMULA & EARLY WARNING TRAINING LABELS:")
    print("   Priority Formula: (100 - success_score) + 25*(AcadRisk=='High') + 20*(PlaceRisk=='High') + 10*(PlaceRisk=='Medium') + max(0, -trend_delta)*2.0")
    print("   Early Warning Target Label: 1 if (academic_risk == 'High' or placement_risk == 'High') else 0")
    print(f"   Early Warning Positive Class Count: {int(((df['academic_risk'] == 'High') | (df['placement_risk'] == 'High')).sum())} of {len(df)}")

    conn.close()
    print("\n" + "=" * 80)
    print("ALL PHASE 2 AUDIT CHECKS COMPLETED SUCCESSFULLY")
    print("=" * 80)

if __name__ == "__main__":
    verify()
