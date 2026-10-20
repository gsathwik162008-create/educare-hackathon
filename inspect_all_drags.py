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
    # Let's inspect ALL drivers
    drivers = []
    from core.config import DRIVER_INDICATORS
    for col, (label, weight) in DRIVER_INDICATORS.items():
        val = norm_row.get(col, 0.0)
        mean_val = cohort_means.get(col, 50.0)
        diff = val - mean_val
        impact = round(float(weight * diff), 2)
        drivers.append({"col": col, "label": label, "impact": impact, "diff": round(diff, 1)})
    
    drags = [d for d in drivers if d["impact"] < 0]
    drags.sort(key=lambda x: x["impact"])
    print(f"\nStudent: {sid} {row['name']}")
    for d in drags:
        print(f"  {d['label']:<24}: impact={d['impact']:+.2f} pts (diff={d['diff']:+.1f})")

conn.close()
