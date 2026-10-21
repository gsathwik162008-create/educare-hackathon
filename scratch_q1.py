import sqlite3
import pandas as pd
from core.ingest import ingest_all

stats = ingest_all(verbose=True)
conn = sqlite3.connect('data/campus.db')
u = pd.read_sql('SELECT student_id, cgpa FROM students_unified', conn)
s = pd.read_sql('SELECT student_id, semester, cgpa FROM semester_history', conn)
last_sem = s.sort_values(['student_id', 'semester']).groupby('student_id').last().reset_index()
merged = pd.merge(u, last_sem, on='student_id', suffixes=('_u', '_hist'))
diffs = (merged['cgpa_u'] - merged['cgpa_hist']).abs()
print("=== QUESTION 1 VERIFICATION ===")
print(f"Total students verified: {len(merged)}")
print(f"Students differing by > 0.001: {(diffs > 0.001).sum()}")
print(f"Students differing by > 0.3: {(diffs > 0.3).sum()}")
print(f"Max difference: {diffs.max():.6f}")

log = pd.read_sql("SELECT * FROM cleaning_log WHERE file='semester_history.csv'", conn)
print("\nCleaning Log for semester_history.csv:")
for _, row in log.iterrows():
    print(dict(row))
conn.close()
