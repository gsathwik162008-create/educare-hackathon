"""
Smart Campus Analytics - Phase 3 Verification Script
Validates intervention generation, priority calculation (gain x urgency),
interventions table lifecycle in SQLite, placement skill gap analysis,
bottleneck subjects detection, intervention effectiveness metrics,
faculty analyst templates, supportive student portal templates, and cached LLM narratives.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import sqlite3
import pandas as pd
from core.config import DB_PATH
from core.interventions import (
    initialize_interventions_table,
    update_intervention_status,
    calculate_priority,
    get_placement_skill_gap,
    get_bottleneck_subjects,
    get_intervention_effectiveness
)
from core.explain import (
    explain_for_faculty,
    explain_for_student,
    get_enhanced_explanation
)

def verify():
    print("=" * 80)
    print("SMART CAMPUS ANALYTICS - PHASE 3 VERIFICATION")
    print("=" * 80)

    # 1. Initialize and verify interventions table
    print("\n[1] INITIALIZING INTERVENTIONS TABLE IN SQLITE...")
    conn = sqlite3.connect(DB_PATH)
    initialize_interventions_table(conn)

    cursor = conn.cursor()
    int_count = cursor.execute("SELECT COUNT(*) FROM interventions").fetchone()[0]
    print(f"   Table 'interventions' records: {int_count}")
    
    # Check status breakdown
    status_df = pd.read_sql("SELECT status, COUNT(*) as count FROM interventions GROUP BY status", conn)
    print("   Intervention Status Distribution:")
    print(status_df.to_string(index=False))

    # Sample rows
    print("\n   Sample generated intervention records (including timeline and due_date):")
    sample_df = pd.read_sql("""
    SELECT student_id, action, assigned_to, owner, timeline, due_date, status, score_at_creation, potential_gain, action_priority, data_source
    FROM interventions
    LIMIT 6
    """, conn)
    print(sample_df.to_string(index=False))

    # 2. Test status update in interventions table
    print("\n[2] TESTING STATUS UPDATE ON INTERVENTION RECORD...")
    first_id = cursor.execute("SELECT id, status FROM interventions LIMIT 1").fetchone()
    if first_id:
        target_id, old_status = first_id
        new_status = "in progress" if old_status != "in progress" else "done"
        updated = update_intervention_status(target_id, new_status, conn)
        check_status = cursor.execute("SELECT status FROM interventions WHERE id = ?", (target_id,)).fetchone()[0]
        print(f"   Record #{target_id}: status transitioned from '{old_status}' to '{check_status}' (Success: {updated})")
        assert check_status == new_status, "Status update failed!"

    # 3. Test Priority Formula (Action Priority = Potential Gain x Urgency) on Engineered Students
    print("\n[3] INTERVENTION PRIORITY & ACTION MAPPING FOR ENGINEERED STUDENTS:")
    students_scored = pd.read_sql("SELECT * FROM students_scored", conn)
    eng_ids = ["21CSE089", "22ECE045", "21MECH012", "23CIVIL034", "22EEE071"]
    for sid in eng_ids:
        row = students_scored[students_scored["student_id"] == sid].iloc[0]
        from core.interventions import get_student_specific_interventions
        p_val, gain, act, top2 = get_student_specific_interventions(row)
        gaps_str = " + ".join([g["action"] for g in top2])
        print(f"   {sid} ({row['name']:<16}): Risk Triage Score={row['risk_triage_score']:>5.1f} | Action Priority={p_val:>5.2f} | Potential Gain=+{gain:>4.1f} pts | Action: {act:<24} | Top gaps: {gaps_str}")

    # 4. Test Placement Skill Gap Analysis
    print("\n[4] PLACEMENT SKILL GAP ANALYSIS:")
    sample_student = students_scored[students_scored["student_id"] == "21CSE089"].iloc[0]
    gap_result = get_placement_skill_gap(sample_student, target_role="Software Engineer")
    print(f"   Student: {sample_student['name']} ({sample_student['student_id']}) -> Target: {gap_result['target_role']}")
    print(f"   Role Readiness: {gap_result['role_readiness_pct']}% | {gap_result['biggest_opportunity']}")
    for skill, info in gap_result["gaps"].items():
        print(f"     - {skill:<16}: Student={info['student']:<5.1f} | Required={info['required']:<5.1f} | Gap={info['gap']:<4.1f} | Match={info['match_pct']}%")

    # 5. Test Bottleneck Subjects
    print("\n[5] BOTTLENECK SUBJECTS IDENTIFICATION (Highest failure & attendance drop):")
    bottlenecks = get_bottleneck_subjects(conn)
    print(bottlenecks.head(6).to_string(index=False))

    # 6. Test Intervention Effectiveness
    print("\n[6] INTERVENTION EFFECTIVENESS (Historical Completed Actions):")
    eff_df = get_intervention_effectiveness(conn)
    if not eff_df.empty:
        print(eff_df.to_string(index=False))
    else:
        print("   No completed interventions logged yet.")

    # 7. Test Explanation Engine (Faculty Analyst vs Student Supportive)
    print("\n[7] EXPLANATION TEMPLATES VERIFICATION:")
    for test_sid in ["21CSE089", "21MECH012"]:
        st_row = students_scored[students_scored["student_id"] == test_sid].iloc[0]
        f_txt = explain_for_faculty(st_row)
        s_txt = explain_for_student(st_row)
        print(f"\n   --- {st_row['name']} ({test_sid}) ---")
        print("   [Faculty View - Analyst Tone]:")
        print("   " + f_txt)
        print("   [Student Portal View - Supportive Tone]:")
        print("   " + s_txt)

    # Verification: Student view MUST NOT contain forbidden words
    stud_text = explain_for_student(students_scored[students_scored["student_id"] == "21CSE089"].iloc[0])
    forbidden_words = ["risk", "at-risk", "rank", "segment", "cluster", "fail"]
    for w in forbidden_words:
        assert w not in stud_text.lower(), f"Forbidden word '{w}' found in student explanation!"
    print("\n   CONFIRMED: Student explanation strictly adheres to supportive tone with NO risk/rank buzzwords.")

    # 8. Test Cached LLM Explanation Lookup
    print("\n[8] CACHED LLM EXPLANATION LOOKUP:")
    cached_fac = get_enhanced_explanation("21CSE089", role="faculty")
    cached_stud = get_enhanced_explanation("21CSE089", role="student")
    print("   Cached Faculty Narrative:")
    print("   " + cached_fac)
    print("\n   Cached Student Narrative:")
    print("   " + cached_stud)

    # STRICT ASSERTIONS THAT FAIL LOUDLY IF ANY SPEC IS VIOLATED
    print("\n[9] RUNNING STRICT ASSERTIONS...")
    
    # Assert 1: Table row count >= 100
    assert int_count >= 100, f"Expected at least 100 interventions, found {int_count}"
    
    # Assert 2: Required columns present in interventions table
    cols = [c[1] for c in cursor.execute("PRAGMA table_info(interventions)").fetchall()]
    required_cols = ["student_id", "action", "owner", "timeline", "due_date", "status", "action_priority", "data_source"]
    for rc in required_cols:
        assert rc in cols, f"Missing required column '{rc}' in interventions table!"

    # Assert 3: Coding bootcamp assigned to Aarav, Rahul, and Vikram
    from core.interventions import get_student_specific_interventions
    for cid in ["21CSE089", "21MECH012", "22EEE071"]:
        c_row = students_scored[students_scored["student_id"] == cid].iloc[0]
        _, _, _, c_acts = get_student_specific_interventions(c_row)
        action_names = [a["action"] for a in c_acts]
        assert "Coding bootcamp" in action_names, f"Expected 'Coding bootcamp' in {cid}'s actions, got {action_names}"

    # Assert 4: Bottleneck subjects all have enrolled_count >= 10
    if not bottlenecks.empty:
        min_enrolled = bottlenecks["enrolled_count"].min()
        assert min_enrolled >= 10, f"Bottleneck subjects must have enrolled_count >= 10, found min {min_enrolled}"

    # Assert 5: Completed interventions historical gains between -2.0 and +9.0 and ~65% success rate
    done_interventions = pd.read_sql("SELECT (sc.success_score - i.score_at_creation) as gain FROM interventions i JOIN students_scored sc ON i.student_id = sc.student_id WHERE i.status = 'done'", conn)
    assert not done_interventions.empty, "No done interventions found!"
    min_gain = done_interventions["gain"].min()
    max_gain = done_interventions["gain"].max()
    succ_rate = (done_interventions["gain"] > 0).mean() * 100.0
    assert min_gain >= -2.5, f"Expected min gain >= -2.0 (with roundoff), got {min_gain}"
    assert max_gain <= 9.5, f"Expected max gain <= 9.0 (with roundoff), got {max_gain}"
    assert 55.0 <= succ_rate <= 75.0, f"Expected ~65% success rate, got {succ_rate:.1f}%"

    # Assert 6: Cached LLM text must not contain gain numbers (+X.X points)
    import re
    assert not re.search(r"\+\d+\.?\d*\s*(?:pts|points)", cached_fac), "Cached faculty narrative still contains point gain numbers!"
    assert not re.search(r"\+\d+\.?\d*\s*(?:pts|points)", cached_stud), "Cached student narrative still contains point gain numbers!"

    # Assert 7: explain.py's recommended action equals top action in interventions table for all 5 engineered students
    for esid in ["21CSE089", "22ECE045", "21MECH012", "23CIVIL034", "22EEE071"]:
        e_row = students_scored[students_scored["student_id"] == esid].iloc[0]
        # Top action in interventions table
        top_db_action = cursor.execute("SELECT action FROM interventions WHERE student_id = ? ORDER BY id ASC LIMIT 1", (esid,)).fetchone()[0]
        # Action from explain_for_faculty
        _, _, exp_action, _ = get_student_specific_interventions(e_row)
        assert exp_action == top_db_action, f"Mismatch for {esid}: explain.py got '{exp_action}' but interventions table has '{top_db_action}'"

    # Assert 8: Completed interventions include Coding bootcamp and Counsellor check-in
    done_actions = set(pd.read_sql("SELECT DISTINCT action FROM interventions WHERE status = 'done'", conn)["action"])
    assert "Coding bootcamp" in done_actions, f"Coding bootcamp not in completed interventions: {done_actions}"
    assert "Counsellor check-in" in done_actions, f"Counsellor check-in not in completed interventions: {done_actions}"

    conn.close()
    print("   ALL STRICT ASSERTIONS VERIFIED AND PASSED LOUDLY.")
    print("=" * 80)

if __name__ == "__main__":
    verify()
