import sqlite3
from collections import Counter

import pandas as pd

from core.auth import get_students_for_user
from core.score import (
    get_cohort_summary_kpis,
    get_department_year_heatmap,
    get_segment_distribution,
)

conn = sqlite3.connect("data/campus.db")
print("=== TABLES ===")
print(pd.read_sql("SELECT name FROM sqlite_master WHERE type='table'", conn).to_string())

print("\n=== INTERVENTIONS ===")
tables = pd.read_sql("SELECT name FROM sqlite_master WHERE type='table'", conn)["name"].tolist()
if "interventions" in tables:
    ints = pd.read_sql("SELECT * FROM interventions", conn)
    print("interventions row count", len(ints))
    for sid in ["22CSE020", "22CSE594"]:
        sub = ints[ints["student_id"] == sid]
        print(f"{sid} rows", len(sub))
        if sub.empty:
            print(f"NO {sid}")
        else:
            print(sub.to_string(index=False))
else:
    print("NO interventions table")
    ints = None

print("\n=== 22CSE020 / 22CSE594 scored ===")
sc = pd.read_sql(
    "SELECT student_id, name, mentor_id, academic_risk, placement_risk, success_score, risk_triage_score FROM students_scored WHERE student_id IN ('22CSE020','22CSE594')",
    conn,
)
print(sc.to_string(index=False))

print("\n=== FAC_CSE_01 KPIs ===")
user = {"username": "FAC_CSE_01", "role": "FACULTY", "mentor_id": "FAC_CSE_01"}
mentees = get_students_for_user(user, conn=conn)
print("total mentees", len(mentees))
if ints is not None:
    idf = ints[
        ints["student_id"].isin(mentees["student_id"]) | (ints["assigned_to"] == "FAC_CSE_01")
    ]
else:
    idf = pd.DataFrame()
mentee_ids = set(mentees["student_id"])
int_groups = idf.groupby("student_id")["status"].apply(list).to_dict() if not idf.empty else {}
pending = inprog = done = noact = 0
for mid in mentee_ids:
    if mid not in int_groups:
        noact += 1
    else:
        st_list = int_groups[mid]
        if all(s == "done" for s in st_list):
            done += 1
        elif any(s == "in progress" for s in st_list):
            inprog += 1
        else:
            pending += 1
print("pending", pending)
print("in progress", inprog)
print("completed", done)
print("no action", noact)

print("\n=== COHORT OVERVIEW ===")
kpis = get_cohort_summary_kpis(conn=conn)
for k, v in kpis.items():
    print(f"{k}: {v}")
seg = get_segment_distribution(conn=conn)
print("\nSEGMENT COUNTS:")
print(seg.to_string(index=False))
hm = get_department_year_heatmap(conn=conn)
print("\nHEATMAP COUNTS:")
print(hm["count_df"].to_string())
print("heatmap n sum", int(hm["count_df"].values.sum()))

print("\n=== MECH YEAR 2 FALLING ATTENDANCE ===")
mech = pd.read_sql(
    "SELECT student_id, name, year, department, attendance_trend_delta, trend_delta, risk_reasons FROM students_scored WHERE department='Mech' AND year=2",
    conn,
)
print("Mech Y2 n", len(mech))
print("attendance_trend_delta describe:")
print(mech["attendance_trend_delta"].describe().to_string())
print("\nrisk_reasons sample:")
print(mech["risk_reasons"].head(15).to_string())
pat = mech["risk_reasons"].str.contains(
    "falling|attendance trend|Attendance declined|Declining", case=False, na=False
)
print("\nmatching declining/falling pattern", int(pat.sum()))
if pat.any():
    print(
        mech.loc[pat, ["student_id", "attendance_trend_delta", "trend_delta", "risk_reasons"]].to_string()
    )
pat2 = mech["risk_reasons"].str.contains("falling.attendance|Falling attendance", case=False, na=False)
print("falling-attendance specifically", int(pat2.sum()))
print("\nunique reason fragments:")
c = Counter()
for r in mech["risk_reasons"]:
    for part in str(r).split("|"):
        c[part.strip()[:80]] += 1
for k, v in c.most_common():
    print(v, k)

conn.close()
