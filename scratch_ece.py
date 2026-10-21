import sqlite3
import pandas as pd
from core.ingest import standardise_student_id

conn = sqlite3.connect('data/campus.db')
ece_students = pd.read_sql("SELECT student_id FROM students_scored WHERE department='ECE'", conn)['student_id'].tolist()
print('Total ECE students:', len(ece_students))

ece_m4 = pd.read_sql("""
    SELECT a.student_id, a.attendance_pct 
    FROM attendance_history a
    JOIN students_scored s ON a.student_id = s.student_id
    WHERE s.department = 'ECE' AND a.month = 'Month 4'
""", conn)
print('ECE students in Month 4 in campus.db:', len(ece_m4))
missing_in_db = set(ece_students) - set(ece_m4['student_id'])
print(f'Missing ECE student IDs in Month 4 ({len(missing_in_db)}):', sorted(list(missing_in_db)))

# Check raw attendance_history.csv
raw_att = pd.read_csv('data/raw/attendance_history.csv')
raw_att['clean_id'] = standardise_student_id(raw_att['student_id'])

raw_m4_ece = raw_att[(raw_att['clean_id'].isin(ece_students)) & (raw_att['month'] == 'Month 4')]
print('Raw ECE Month 4 rows before cleaning:', len(raw_m4_ece))
print('Unique students in raw ECE Month 4:', raw_m4_ece['clean_id'].nunique())

# Check why missing students have no Month 4 row in raw or db
for sid in sorted(list(missing_in_db))[:5]:
    rows = raw_att[raw_att['clean_id'] == sid]
    print(f"\nStudent {sid} in raw:")
    print(rows[['student_id', 'clean_id', 'month', 'attendance_pct']])

# Check cleaning log for attendance_history
log = pd.read_sql("SELECT * FROM cleaning_log WHERE file='attendance_history.csv'", conn)
print("\nCleaning Log for attendance_history.csv:")
print(log.to_string(index=False))

conn.close()
