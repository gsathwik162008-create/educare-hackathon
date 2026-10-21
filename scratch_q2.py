import sqlite3
import pandas as pd
from core.score import score_all

score_all(verbose=False)
conn = sqlite3.connect('data/campus.db')
df = pd.read_sql('SELECT student_id, name, year, success_score, risk_triage_score, trend_delta, cgpa_trend_delta FROM students_scored', conn)
df['risk_triage_rank'] = df['risk_triage_score'].rank(ascending=False, method='min').astype(int)

aarav = df[df['student_id'] == '21CSE089'].iloc[0]
print("=== AARAV SCORES ===")
print(f"student_id: {aarav['student_id']}")
print(f"name: {aarav['name']}")
print(f"cgpa_trend_delta: {aarav['cgpa_trend_delta']:.4f}")
print(f"trend_delta: {aarav['trend_delta']:.4f}")
print(f"risk_triage_score: {aarav['risk_triage_score']:.2f}")
print(f"risk_triage_rank: {aarav['risk_triage_rank']}")

print("\n=== TOP 10 BY RISK_TRIAGE_SCORE ===")
top10 = df.sort_values(by='risk_triage_score', ascending=False).head(10).reset_index(drop=True)
print(top10[['student_id', 'name', 'risk_triage_score', 'risk_triage_rank', 'trend_delta', 'cgpa_trend_delta']].to_string(index=False))

eng_ids = ['21CSE089', '22ECE045', '21MECH012', '23CIVIL034', '22EEE071']
top10_ids = set(top10['student_id'].values)
print("\n=== 5 ENGINEERED AT-RISK STUDENTS IN TOP 10 ===")
for sid in eng_ids:
    row = df[df['student_id'] == sid].iloc[0]
    in_top10 = sid in top10_ids
    print(f"{sid} ({row['name']}): risk_triage_score={row['risk_triage_score']:.2f}, rank={row['risk_triage_rank']}, in_top10={in_top10}")

conn.close()
