import sqlite3
import pandas as pd

con = sqlite3.connect("data/campus.db")
pd.set_option("display.max_rows", 100, "display.width", 200, "display.max_colwidth", 70)

print("1. COLUMNS")
print(pd.read_sql("PRAGMA table_info(students_unified)", con)[["name", "type"]])

print("\n2. COUNT vs DISTINCT")
print(pd.read_sql("SELECT COUNT(*) AS total, COUNT(DISTINCT student_id) AS uniq FROM students_unified", con))

print("\n3. ENGINEERED STUDENTS")
print(pd.read_sql("""SELECT student_id, cgpa, backlogs, attendance_pct, coding
FROM students_unified
WHERE student_id IN ('23CIVIL034','21CSE089','22ECE045','21MECH012','22EEE071')""", con))

print("\n4. CLEANING LOG")
print(pd.read_sql("SELECT file, issue_type, rows_affected, action FROM cleaning_log", con))