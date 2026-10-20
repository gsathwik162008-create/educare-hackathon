"""
Smart Campus Analytics - Faculty Intervention Queue
Role Guard: FACULTY and ADMIN only.
Data is scoped strictly via core.auth.get_interventions_for_user(user).
Shows each student once (grouped actions), single combined gain, interactive status updates,
and an insight header computed from the live dataset.
"""

import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime, timedelta
from core.config import DB_PATH
from core.auth import get_interventions_for_user, get_students_for_user
from core.interventions import update_intervention_status

st.set_page_config(
    page_title="Faculty Intervention Queue",
    page_icon="📋",
    layout="wide"
)

# Custom CSS
st.markdown("""
<style>
    .demo-tag {
        display: inline-block;
        padding: 3px 10px;
        background-color: #FEF3C7;
        color: #92400E;
        font-size: 0.8rem;
        font-weight: 700;
        border-radius: 4px;
        border: 1px solid #F59E0B;
        margin-bottom: 8px;
    }
    .metric-card {
        background: #1E293B;
        border: 1px solid #334155;
        border-radius: 8px;
        padding: 16px;
        text-align: center;
    }
    .metric-num {
        font-size: 1.8rem;
        font-weight: 700;
        color: #38BDF8;
    }
    .metric-lbl {
        font-size: 0.85rem;
        color: #94A3B8;
    }
    .insight-banner {
        padding: 12px 18px;
        background: rgba(56, 189, 248, 0.1);
        border-left: 4px solid #38BDF8;
        border-radius: 6px;
        font-size: 1.05rem;
        font-weight: 600;
        color: #F8FAFC;
        margin-bottom: 18px;
    }
</style>
""", unsafe_allow_html=True)

# 1. Role Guard
user = st.session_state.get("user")
if not st.session_state.get("authenticated") or not user:
    st.error("⛔ Authentication Required: Please log in on the main portal page.")
    st.stop()

role = user.get("role", "").upper()
if role not in ["FACULTY", "ADMIN"]:
    st.error(f"⛔ Access Denied: Role '{role}' is not authorized to view the Faculty Intervention Queue.")
    st.stop()

# Header
st.title("📋 Faculty Intervention Queue")

# 2. Fetch Scoped Data
conn = sqlite3.connect(DB_PATH)
interventions_df = get_interventions_for_user(user, conn=conn)
mentees_df = get_students_for_user(user, table_name="students_scored", conn=conn)
conn.close()

if interventions_df.empty:
    st.info("No intervention records found for your assigned scope.")
    st.stop()

# Join with student demographic & risk scores
if "name" not in interventions_df.columns:
    interventions_df = interventions_df.merge(
        mentees_df[["student_id", "name", "risk_triage_score", "department", "year"]],
        on="student_id",
        how="left"
    )

# 3. Dynamic Insight Sentence Calculation
total_mentees = len(mentees_df)
today = datetime.now()
next_week = (today + timedelta(days=7)).strftime("%Y-%m-%d")

# Actions needing action this week: pending/in progress with due_date <= next_week
due_soon_mask = (interventions_df["status"].isin(["pending", "in progress"])) & (interventions_df["due_date"] <= next_week)
students_due_soon = interventions_df[due_soon_mask]["student_id"].nunique()

insight_sentence = f"💡 {total_mentees} mentees in scope; {students_due_soon} students need action within the next 7 days."
st.markdown(f'<div class="insight-banner">{insight_sentence}</div>', unsafe_allow_html=True)

# Metric Summary Cards
c1, c2, c3, c4 = st.columns(4)
with c1:
    st.markdown(f'<div class="metric-card"><div class="metric-num">{total_mentees}</div><div class="metric-lbl">Total Mentees</div></div>', unsafe_allow_html=True)
with c2:
    pending_cnt = (interventions_df["status"] == "pending").sum()
    st.markdown(f'<div class="metric-card"><div class="metric-num">{pending_cnt}</div><div class="metric-lbl">Pending Actions</div></div>', unsafe_allow_html=True)
with c3:
    in_prog_cnt = (interventions_df["status"] == "in progress").sum()
    st.markdown(f'<div class="metric-card"><div class="metric-num">{in_prog_cnt}</div><div class="metric-lbl">In Progress</div></div>', unsafe_allow_html=True)
with c4:
    done_cnt = (interventions_df["status"] == "done").sum()
    st.markdown(f'<div class="metric-card"><div class="metric-num">{done_cnt}</div><div class="metric-lbl">Completed (Done)</div></div>', unsafe_allow_html=True)

st.write("")

# 4. Filter and Search Controls
col_f1, col_f2, col_f3 = st.columns([2, 2, 3])
with col_f1:
    status_filter = st.multiselect("Filter by Status", options=["pending", "in progress", "done"], default=["pending", "in progress", "done"])
with col_f2:
    sort_by = st.selectbox("Sort By", options=["Action Priority (High to Low)", "Risk Triage Score (High to Low)", "Earliest Due Date"])
with col_f3:
    search_query = st.text_input("Search student name or roll number", placeholder="e.g. Aarav, 21CSE089")

# Apply filters
filtered_df = interventions_df.copy()
if status_filter:
    filtered_df = filtered_df[filtered_df["status"].isin(status_filter)]
if search_query:
    q = search_query.strip().lower()
    filtered_df = filtered_df[
        filtered_df["name"].str.lower().str.contains(q, na=False) |
        filtered_df["student_id"].str.lower().str.contains(q, na=False)
    ]

# 5. Group Actions by Student (Count combined potential gain once per student)
grouped_records = []
for sid, group in filtered_df.groupby("student_id", sort=False):
    first_row = group.iloc[0]
    # Unique actions list
    actions_list = group["action"].tolist()
    actions_str = " + ".join(actions_list)
    owners_str = ", ".join(group["owner"].unique().tolist())
    statuses_list = group["status"].tolist()
    # Earliest due date
    min_due = group["due_date"].min()
    # Overall student action status
    overall_status = "done" if all(s == "done" for s in statuses_list) else ("in progress" if any(s == "in progress" for s in statuses_list) else "pending")
    # Action priority and potential gain (taken once from student level)
    pot_gain = first_row["potential_gain"]
    act_prio = first_row["action_priority"]
    triage_score = first_row["risk_triage_score"]

    grouped_records.append({
        "student_id": sid,
        "name": first_row["name"],
        "risk_triage_score": triage_score,
        "action": actions_str,
        "owner": owners_str,
        "due_date": min_due,
        "status": overall_status,
        "action_priority": act_prio,
        "potential_gain": pot_gain,
        "action_ids": group["id"].tolist()
    })

queue_df = pd.DataFrame(grouped_records)

# Apply Sorting
if not queue_df.empty:
    if "Action Priority" in sort_by:
        queue_df = queue_df.sort_values(by="action_priority", ascending=False)
    elif "Risk Triage Score" in sort_by:
        queue_df = queue_df.sort_values(by="risk_triage_score", ascending=False)
    elif "Due Date" in sort_by:
        queue_df = queue_df.sort_values(by="due_date", ascending=True)

# 6. Display Intervention Queue Table
st.markdown('<div class="demo-tag">DEMO DATA — SYNTHETIC BENCHMARK & TRACKING</div>', unsafe_allow_html=True)

if queue_df.empty:
    st.warning("No students match the current filter selection.")
else:
    # Display interactive overview table
    display_view = queue_df[[
        "name", "student_id", "risk_triage_score", "action", "owner",
        "due_date", "status", "action_priority", "potential_gain"
    ]].copy()
    display_view.columns = [
        "Student Name", "Roll ID", "Risk Triage Score", "Recommended Actions",
        "Action Owner", "Due Date", "Current Status", "Action Priority", "Simulated Gain (+pts)"
    ]

    st.dataframe(
        display_view,
        use_container_width=True,
        hide_index=True
    )

    st.write("---")
    st.subheader("📝 Update Mentee Intervention Status")
    st.caption("Select a student to update the status in SQLite. Changes persist across page reloads.")

    up_col1, up_col2, up_col3 = st.columns([3, 2, 2])
    with up_col1:
        student_choices = queue_df.apply(lambda r: f"{r['name']} ({r['student_id']}) - {r['action']}", axis=1).tolist()
        selected_choice = st.selectbox("Select Student Action", options=student_choices)
        selected_sid = selected_choice.split("(")[1].split(")")[0]
        selected_student_group = queue_df[queue_df["student_id"] == selected_sid].iloc[0]

    with up_col2:
        current_st = selected_student_group["status"]
        status_options = ["pending", "in progress", "done"]
        default_idx = status_options.index(current_st) if current_st in status_options else 0
        new_status = st.selectbox("New Status", options=status_options, index=default_idx)

    with up_col3:
        st.write("")
        st.write("")
        if st.button("💾 Persist Status Update", use_container_width=True):
            conn = sqlite3.connect(DB_PATH)
            for act_id in selected_student_group["action_ids"]:
                update_intervention_status(act_id, new_status, conn=conn)
            conn.close()
            st.success(f"Updated status for {selected_student_group['name']} to '{new_status}'!")
            st.rerun()
