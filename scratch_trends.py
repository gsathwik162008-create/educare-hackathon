import sqlite3
import pandas as pd
from core.score import get_trends_data

conn = sqlite3.connect('data/campus.db')
trends = get_trends_data(conn=conn)

print("=" * 80)
print("1. INSIGHT TITLE")
print("=" * 80)
print(trends["insight_title"])

print("\n" + "=" * 80)
print("2. RAW TABLE: SEMESTER CGPA TREND BY ADMISSION COHORT (YEARS 1..4)")
print("=" * 80)
print(trends["semester_cgpa_by_cohort"].to_string())

print("\n" + "=" * 80)
print("3. RAW TABLE: MONTHLY ATTENDANCE TREND BY DEPARTMENT (4 MONTHS)")
print("=" * 80)
print(trends["monthly_attendance_by_dept"].to_string())

print("\n" + "=" * 80)
print("4. RAW TABLE: WEEKLY LMS LOGINS TREND BY DEPARTMENT (8 WEEKS)")
print("=" * 80)
print(trends["weekly_lms_by_dept"].to_string())

print("\n" + "=" * 80)
print("5. RAW TABLE: DEPARTMENT COMPARISON TABLE")
print("=" * 80)
print(trends["department_comparison"].to_string(index=False))

print("\n" + "=" * 80)
print("6. SQL CROSS-CHECK: ECE MONTH 4 ATTENDANCE")
print("=" * 80)
sql_ece_m4 = """
SELECT 
    s.department,
    a.month,
    ROUND(AVG(a.attendance_pct), 2) as mean_attendance,
    COUNT(*) as row_count,
    COUNT(DISTINCT a.student_id) as student_count
FROM attendance_history a
JOIN students_scored s ON a.student_id = s.student_id
WHERE s.department = 'ECE' AND a.month = 'Month 4'
GROUP BY s.department, a.month
"""
df_check = pd.read_sql(sql_ece_m4, conn)
print("SQL Query:\n", sql_ece_m4.strip())
print("\nResult:")
print(df_check.to_string(index=False))

conn.close()
