import sqlite3
import pandas as pd
from core.score import compute_indicator_drivers, normalize_metrics

conn = sqlite3.connect("data/campus.db")
scored = pd.read_sql("SELECT * FROM students_scored", conn)
norm = normalize_metrics(scored)
cohort_means = norm.mean().to_dict()

eng_ids = ["21CSE089", "21MECH012", "23CIVIL034", "22ECE045", "22EEE071"]
for sid in eng_ids:
    row = scored[scored["student_id"] == sid].iloc[0]
    norm_row = norm.loc[row.name].to_dict()
    _, _, drags_list, _ = compute_indicator_drivers(norm_row, cohort_means)
    print(f"\nStudent: {sid} {row['name']}")
    non_cgpa = [d for d in drags_list if d['label'] != 'CGPA']
    print("All drags:", [d['label'] + f" ({d['impact']})" for d in drags_list])
    print("Top non-CGPA drags:", [d['label'] + f" ({d['impact']})" for d in non_cgpa])

conn.close()
