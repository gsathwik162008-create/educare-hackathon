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
from core.config import DB_PATH, DEMO_TODAY
from core.auth import get_interventions_for_user, get_students_for_user
from core.interventions import update_intervention_status
from core.ui import load_css, render_kpi_card, render_insight_header, render_demo_badge

st.set_page_config(
    page_title="Faculty Intervention Queue | Smart Campus Analytics",
    layout="wide"
)

# Load Institutional Design System
load_css()

# 1. Role Guard
user = st.session_state.get("user")
if not st.session_state.get("authenticated") or not user:
    st.error("Authentication Required: Please log in on the main portal page.")
    st.stop()

role = user.get("role", "").upper()
if role not in ["FACULTY", "ADMIN"]:
    st.error(f"Access Denied: Role '{role}' is not authorized to view the Faculty Intervention Queue.")
    st.stop()

# Header
st.title("Faculty Intervention Queue")

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
today = datetime.strptime(DEMO_TODAY, "%Y-%m-%d")
next_week = (today + timedelta(days=7)).strftime("%Y-%m-%d")

# Actions needing action this week: pending/in progress with due_date <= next_week
due_soon_mask = (interventions_df["status"].isin(["pending", "in progress"])) & (interventions_df["due_date"] <= next_week)
students_due_soon = interventions_df[due_soon_mask]["student_id"].nunique()

insight_sentence = f"Cohort Summary: {total_mentees} mentees in assigned scope. {students_due_soon} students require intervention action within the next 7 days."
render_insight_header(insight_sentence)

# Metric Summary KPI Cards (White background, 1px border #DDE3EC, 4px radius, KPMG navy number, small grey uppercase label)
c1, c2, c3, c4 = st.columns(4)
with c1:
    render_kpi_card(total_mentees, "Total Mentees")
with c2:
    pending_cnt = int((interventions_df["status"] == "pending").sum())
    render_kpi_card(pending_cnt, "Pending Actions")
with c3:
    in_prog_cnt = int((interventions_df["status"] == "in progress").sum())
    render_kpi_card(in_prog_cnt, "In Progress")
with c4:
    done_cnt = int((interventions_df["status"] == "done").sum())
    render_kpi_card(done_cnt, "Completed")

# 4. Filter and Search Controls
col_f1, col_f2, col_f3 = st.columns([2, 2, 3])
with col_f1:
    status_filter = st.multiselect("Filter by Status", options=["pending", "in progress", "done"], default=["pending", "in progress", "done"])
with col_f2:
    sort_by = st.selectbox("Sort By", options=["Action Priority (High to Low)", "Risk Triage Score (High to Low)", "Earliest Due Date"])
with col_f3:
    search_query = st.text_input("Search Student Name or Roll Number", placeholder="e.g. Aarav, 21CSE089")

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
    actions_list = group["action"].tolist()
    actions_str = " + ".join(actions_list)
    owners_str = ", ".join(group["owner"].unique().tolist())
    statuses_list = group["status"].tolist()
    min_due = group["due_date"].min()
    overall_status = "done" if all(s == "done" for s in statuses_list) else ("in progress" if any(s == "in progress" for s in statuses_list) else "pending")
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

render_demo_badge()

# 6. Main Layout: Left = Intervention Queue Table, Right = Action Update Panel
left_col, right_col = st.columns([7, 3])

with left_col:
    st.subheader("Prioritized Mentee Backlog")
    if queue_df.empty:
        st.warning("No students match the current filter selection.")
    else:
        display_view = queue_df[[
            "name", "student_id", "risk_triage_score", "action", "owner",
            "due_date", "status", "action_priority", "potential_gain"
        ]].copy()
        display_view.columns = [
            "Student Name", "Roll ID", "Risk Triage Score", "Recommended Actions",
            "Action Owner", "Due Date", "Current Status", "Action Priority", "Simulated Gain (+pts)"
        ]

        # Compact table with sticky header and right-aligned numbers
        st.dataframe(
            display_view,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Risk Triage Score": st.column_config.NumberColumn(format="%.1f"),
                "Action Priority": st.column_config.NumberColumn(format="%.2f"),
                "Simulated Gain (+pts)": st.column_config.NumberColumn(format="+%.1f pts"),
            }
        )

with right_col:
    st.subheader("Update Status")
    with st.expander("Intervention Action Form", expanded=True):
        if queue_df.empty:
            st.caption("No records available to update.")
        else:
            student_choices = queue_df.apply(lambda r: f"{r['name']} ({r['student_id']}) - {r['action']}", axis=1).tolist()
            selected_choice = st.selectbox("Select Mentee Action", options=student_choices)
            selected_sid = selected_choice.split("(")[1].split(")")[0]
            selected_student_group = queue_df[queue_df["student_id"] == selected_sid].iloc[0]

            current_st = selected_student_group["status"]
            status_options = ["pending", "in progress", "done"]
            default_idx = status_options.index(current_st) if current_st in status_options else 0
            new_status = st.selectbox("New Lifecycle Status", options=status_options, index=default_idx)

            st.write("")
            if st.button("Persist Status Update", use_container_width=True, type="primary"):
                conn = sqlite3.connect(DB_PATH)
                for act_id in selected_student_group["action_ids"]:
                    update_intervention_status(act_id, new_status, user=user, conn=conn)
                conn.close()
                st.success(f"Updated status for {selected_student_group['name']} to '{new_status}'.")
                st.rerun()
