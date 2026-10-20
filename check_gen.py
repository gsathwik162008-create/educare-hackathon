import sqlite3
import pandas as pd

conn = sqlite3.connect("data/campus.db")
gen = pd.read_sql("SELECT student_id, name, department, year FROM students_unified WHERE mentor_id = 'FAC_GEN_01'", conn)
print("=== FAC_GEN_01 STUDENTS (Total:", len(gen), ") ===")
print(gen.to_string(index=False))

print("\n=== DEPARTMENT DISTRIBUTION FOR FAC_GEN_01 ===")
print(gen['department'].value_counts().to_string())

conn.close()
