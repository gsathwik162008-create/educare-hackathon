import sqlite3
import pandas as pd
from core.score import score_all
from core.interventions import initialize_interventions_table

print("1. Running score_all...")
score_all(verbose=True)

print("\n2. Initializing interventions table...")
conn = sqlite3.connect("data/campus.db")
initialize_interventions_table(conn)

print("\n3. Checking Nandini Banerjee (24EEE492)...")
df = pd.read_sql("SELECT student_id, name, year, success_score, risk_triage_score, trend_delta, cgpa_trend_delta FROM students_scored", conn)
df["risk_triage_rank"] = df["risk_triage_score"].rank(ascending=False, method="min")
nandini = df[df["student_id"] == "24EEE492"]
print(nandini.to_string(index=False))

print("\n4. Checking sample interventions...")
sample_int = pd.read_sql("SELECT student_id, action, owner, timeline, due_date, status, score_at_creation, potential_gain, action_priority, data_source FROM interventions LIMIT 5", conn)
print(sample_int.to_string(index=False))

conn.close()
