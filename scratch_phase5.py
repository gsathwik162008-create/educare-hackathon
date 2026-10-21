import sqlite3
import pandas as pd
from core.score import get_cohort_summary_kpis, get_department_year_heatmap

conn = sqlite3.connect('data/campus.db')

print("=" * 80)
print("1. RAW KPI VALUES (PYTHON / SQL VERIFICATION)")
print("=" * 80)
kpis = get_cohort_summary_kpis(conn=conn)
for k, v in kpis.items():
    print(f"{k:<30}: {v}")

print("\n" + "=" * 80)
print("2. DIRECT SQL QUERIES MATCHING KPIS")
print("=" * 80)
sql_total = pd.read_sql("SELECT COUNT(*) as n FROM students_scored", conn).iloc[0]["n"]
sql_mean = pd.read_sql("SELECT ROUND(AVG(success_score), 2) as mean_score FROM students_scored", conn).iloc[0]["mean_score"]
sql_acad = pd.read_sql("SELECT COUNT(*) as n FROM students_scored WHERE academic_risk = 'High'", conn).iloc[0]["n"]
sql_place = pd.read_sql("SELECT COUNT(*) as n FROM students_scored WHERE placement_risk = 'High'", conn).iloc[0]["n"]
sql_conf = pd.read_sql("SELECT COUNT(*) as n FROM students_scored WHERE low_confidence = 1", conn).iloc[0]["n"]

print(f"SQL COUNT(*):                     {sql_total}")
print(f"SQL AVG(success_score):           {sql_mean}")
print(f"SQL academic_risk = 'High':       {sql_acad}")
print(f"SQL placement_risk = 'High':      {sql_place}")
print(f"SQL low_confidence = 1:           {sql_conf}")

print("\n" + "=" * 80)
print("3. HEATMAP TABLE (DEPARTMENT x YEAR MEAN SUCCESS SCORE & COUNTS)")
print("=" * 80)
hm = get_department_year_heatmap(conn=conn)
print("MEAN SUCCESS SCORE TABLE:")
print(hm["mean_df"].to_string())
print("\nSTUDENT COUNTS (N) TABLE:")
print(hm["count_df"].to_string())
conn.close()
