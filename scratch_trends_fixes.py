import sqlite3
import pandas as pd
from scripts.seed import ENGINEERED_STUDENTS
from core.score import get_trends_data

conn = sqlite3.connect('data/campus.db')
db_students = pd.read_sql('SELECT * FROM students_unified', conn).set_index('student_id')

all_match = True
print("=" * 80)
print("1. VERIFICATION: ALL 8 ENGINEERED STUDENTS UNCHANGED")
print("=" * 80)
for eng in ENGINEERED_STUDENTS:
    sid = eng['student_id']
    row = db_students.loc[sid]
    for k in ['cgpa', 'backlogs', 'attendance_pct', 'lms_logins_avg', 'coding', 'aptitude', 'technical_score', 'softskill_score']:
        expected = eng[k]
        actual = row[k]
        if abs(expected - actual) > 0.001:
            all_match = False
            print(f"MISMATCH on {sid} {k}: actual={actual}, expected={expected}")
    name = eng['name']
    print(f"   [OK] {sid:<12} ({name:<16}): CGPA={row['cgpa']} | Attendance={row['attendance_pct']}% | LMS={row['lms_logins_avg']}")

print(f"\nResult: All 8 engineered students core attributes identical: {all_match}")

print("\n" + "=" * 80)
print("2. NEW TABLE 2: MONTHLY ATTENDANCE TREND BY DEPARTMENT (4 MONTHS)")
print("=" * 80)
trends = get_trends_data(conn=conn)
print(trends["monthly_attendance_by_dept"].to_string())

# Specifically Mech Year 2 breakdown:
att_raw = pd.read_sql("""
    SELECT s.department, s.year, a.month, ROUND(AVG(a.attendance_pct), 2) as mean_att, COUNT(*) as n
    FROM attendance_history a
    JOIN students_scored s ON a.student_id = s.student_id
    WHERE s.department = 'Mech' AND s.year = 2
    GROUP BY a.month
""", conn)
print("\nMech Year 2 attendance breakdown across months:")
print(att_raw.to_string(index=False))

print("\n" + "=" * 80)
print("3. NEW TABLE 3: WEEKLY LMS LOGINS TREND BY DEPARTMENT (8 WEEKS)")
print("=" * 80)
print(trends["weekly_lms_by_dept"].to_string())

# Specifically CSE Year 3 breakdown:
lms_raw = pd.read_sql("""
    SELECT s.department, s.year, l.week, ROUND(AVG(l.logins), 2) as mean_logins, COUNT(*) as n
    FROM lms_history l
    JOIN students_scored s ON l.student_id = s.student_id
    WHERE s.department = 'CSE' AND s.year = 3
    GROUP BY l.week
""", conn)
print("\nCSE Year 3 weekly LMS logins breakdown (Weeks 1 to 8):")
print(lms_raw.to_string(index=False))

print("\n" + "=" * 80)
print("4. TOP 10 TRIAGE LIST (STUDENTS_SCORED)")
print("=" * 80)
top10 = pd.read_sql("""
    SELECT student_id, name, department, year, success_score, risk_triage_score, academic_risk, placement_risk, risk_reasons
    FROM students_scored
    ORDER BY risk_triage_score DESC
    LIMIT 10
""", conn)
print(top10.to_string(index=False))

print("\n" + "=" * 80)
print("5. INSIGHT TITLE CHECK")
print("=" * 80)
print("Insight title:\n", trends["insight_title"])

conn.close()
