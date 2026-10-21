"""
Smart Campus Analytics - Longitudinal Trends & Multi-Cohort Trajectories
Role Guard: ADMIN and FACULTY.
- ADMIN views full institutional cohort.
- FACULTY views strictly their own advisory mentees (scoped via core.auth.get_students_for_user).
- STUDENT is denied access.
All aggregations, time-series, and insight metrics are computed in core/score.py.
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px

from core.ui import load_css, render_insight_header
from core.auth import get_students_for_user
from core.score import get_trends_data

# Load Institutional Design System
load_css()

# 1. Role Guard
user = st.session_state.get("user")
if not st.session_state.get("authenticated") or not user:
    st.error("Authentication Required: Please log in on the main portal page.")
    st.stop()

role = user.get("role", "").upper()
if role not in ["ADMIN", "FACULTY"]:
    st.error(f"Access Denied: Role '{role}' is not authorized to view Longitudinal Trends.")
    st.stop()

# 2. Scope Determination
# For ADMIN: full population (or filtered).
# For FACULTY: strictly scoped mentees.
scoped_df = get_students_for_user(user, table_name="students_scored")
if scoped_df.empty:
    st.info("No student records available within your assigned scope.")
    st.stop()

# 3. Header & Scope Indicator
st.title("Longitudinal Trends & Multi-Cohort Trajectories")
scope_label = "Institutional Population (All Departments)" if role == "ADMIN" else f"Faculty Advisory Scope ({len(scoped_df)} Mentees)"
st.caption(f"Historical multi-cohort analysis across academic performance, monthly attendance, and digital platform engagement | Scope: {scope_label}")

# 4. Controls: Department Filter and Year Filter
col_c1, col_c2 = st.columns(2)
with col_c1:
    available_depts = sorted(scoped_df["department"].dropna().unique().tolist())
    selected_depts = st.multiselect("Filter Departments", options=available_depts, default=available_depts)

with col_c2:
    available_years = sorted([int(y) for y in scoped_df["year"].dropna().unique().tolist()])
    year_options = [f"Year {y}" for y in available_years]
    selected_years_str = st.multiselect("Filter Admission Cohorts", options=year_options, default=year_options)
    selected_years = [int(y_str.replace("Year ", "")) for y_str in selected_years_str]

# Filter scoped students based on UI controls
filtered_df = scoped_df[
    (scoped_df["department"].isin(selected_depts)) &
    (scoped_df["year"].astype(int).isin(selected_years))
]

if filtered_df.empty:
    st.warning("No students match the selected department and cohort filters.")
    st.stop()

scoped_sids = filtered_df["student_id"].tolist()

# 5. Fetch Trends Data from core/
trends_data = get_trends_data(scoped_student_ids=scoped_sids)

# 6. Insight Title (computed from data in core/)
render_insight_header(trends_data["insight_title"])

# Alerts Box for Flagged Groups (scanning all 20 Department x Year groups)
if trends_data.get("flagged_alerts"):
    for alert in trends_data["flagged_alerts"]:
        st.warning(f"**Cohort Alert — {alert['group']}**: {alert['reasons']}.")

# 7. Note: Do not fabricate a historical success score
st.caption("Note: Longitudinal trends evaluate verified historical records for CGPA, monthly attendance rates, and LMS logins; success score is a point-in-time composite diagnostic and is not fabricated retrospectively.")

st.write("---")

# 8. Chart 1: Semester CGPA Trend by Admission Year Cohort (one thin line per cohort, direct labels, no legend)
st.subheader("Semester CGPA Trajectory by Admission Year Cohort")
st.caption("Cohorts differ in history length. Tracking cumulative grade trajectory by entry cohort (unpooled to prevent survivorship and cohort mixing bias).")

sem_df = trends_data["semester_cgpa_by_cohort"]

if not sem_df.empty:
    fig_cgpa = go.Figure()
    cohort_colors = {
        1.0: "#005EB8",  # Medium Blue
        2.0: "#00338D",  # Navy
        3.0: "#4C7A4F",  # Sage Green
        4.0: "#68737D"   # Neutral Slate
    }

    for yr in sem_df.index:
        row = sem_df.loc[yr].dropna()
        if row.empty:
            continue
        sem_nums = [int(s) for s in row.index]
        cgpa_vals = row.values.tolist()
        color = cohort_colors.get(float(yr), "#00338D")

        # Line trace
        fig_cgpa.add_trace(go.Scatter(
            x=sem_nums,
            y=cgpa_vals,
            mode="lines+markers",
            name=f"Current year {int(yr)}",
            line=dict(color=color, width=2.0),
            marker=dict(size=6, color=color),
            showlegend=False
        ))

        # Direct label at the end of the line
        last_x = sem_nums[-1]
        last_y = cgpa_vals[-1]
        fig_cgpa.add_annotation(
            x=last_x,
            y=last_y,
            text=f" Current year {int(yr)} ({last_y:.2f})",
            showarrow=False,
            xanchor="left",
            yanchor="middle",
            font=dict(size=11, color=color)
        )

    fig_cgpa.update_layout(
        height=320,
        margin=dict(l=20, r=90, t=20, b=20),
        xaxis=dict(title="Semester Number", dtick=1, range=[0.8, 8.8]),
        yaxis=dict(title="Cumulative CGPA", range=[min(6.5, sem_df.min().min() - 0.2), max(8.5, sem_df.max().max() + 0.2)]),
        paper_bgcolor="#FFFFFF",
        plot_bgcolor="#F8FAFD",
        showlegend=False
    )
    st.plotly_chart(fig_cgpa, use_container_width=True)
else:
    st.info("No semester history available for selected cohort filter.")

st.write("---")

# 9. Chart 2 & 3: Monthly Attendance & Weekly LMS Logins by Department
col_t1, col_t2 = st.columns(2)

with col_t1:
    st.subheader("Monthly Attendance Rate by Department")
    st.caption("Tracking 4-month longitudinal attendance percentage across departments.")
    att_df = trends_data["monthly_attendance_by_dept"]

    if not att_df.empty:
        fig_att = go.Figure()
        dept_colors = {
            "CSE": "#00338D",
            "Civil": "#C9922E",
            "ECE": "#005EB8",
            "EEE": "#4C7A4F",
            "Mech": "#B5412F"
        }

        for dept in att_df.index:
            row = att_df.loc[dept].dropna()
            color = dept_colors.get(dept, "#00338D")
            fig_att.add_trace(go.Scatter(
                x=list(row.index),
                y=list(row.values),
                mode="lines+markers",
                name=dept,
                line=dict(color=color, width=2.0),
                marker=dict(size=5, color=color)
            ))

        fig_att.update_layout(
            height=300,
            margin=dict(l=20, r=20, t=20, b=20),
            xaxis_title="Reporting Month",
            yaxis_title="Attendance Rate (%)",
            paper_bgcolor="#FFFFFF",
            plot_bgcolor="#F8FAFD",
            legend=dict(orientation="h", y=1.12, x=0.5, xanchor="center")
        )
        st.plotly_chart(fig_att, use_container_width=True)
    else:
        st.info("No attendance trends for selected scope.")

with col_t2:
    st.subheader("Weekly LMS Logins by Department")
    st.caption("Average weekly login frequency over the active 8-week monitoring window.")
    lms_df = trends_data["weekly_lms_by_dept"]

    if not lms_df.empty:
        fig_lms = go.Figure()
        dept_colors = {
            "CSE": "#00338D",
            "Civil": "#C9922E",
            "ECE": "#005EB8",
            "EEE": "#4C7A4F",
            "Mech": "#B5412F"
        }

        for dept in lms_df.index:
            row = lms_df.loc[dept].dropna()
            color = dept_colors.get(dept, "#00338D")
            fig_lms.add_trace(go.Scatter(
                x=list(row.index),
                y=list(row.values),
                mode="lines+markers",
                name=dept,
                line=dict(color=color, width=2.0),
                marker=dict(size=5, color=color)
            ))

        fig_lms.update_layout(
            height=300,
            margin=dict(l=20, r=20, t=20, b=20),
            xaxis_title="Monitoring Week",
            yaxis_title="Mean Logins / Student",
            paper_bgcolor="#FFFFFF",
            plot_bgcolor="#F8FAFD",
            legend=dict(orientation="h", y=1.12, x=0.5, xanchor="center")
        )
        st.plotly_chart(fig_lms, use_container_width=True)
    else:
        st.info("No LMS activity records for selected scope.")

st.write("---")

# 10. Department Comparison Table: mean CGPA, attendance, LMS logins, assignment completion, n per department, right-aligned
st.subheader("Cross-Department Performance Comparison")
st.caption("Standardized aggregate metrics across academic health and digital platform engagement.")

dept_comp_df = trends_data["department_comparison"]

if not dept_comp_df.empty:
    st.dataframe(
        dept_comp_df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "department": st.column_config.TextColumn("Department"),
            "n": st.column_config.NumberColumn("Students (n)", format="%d"),
            "mean_cgpa": st.column_config.NumberColumn("Mean CGPA", format="%.2f"),
            "mean_attendance": st.column_config.NumberColumn("Mean Attendance (%)", format="%.2f%%"),
            "mean_lms": st.column_config.NumberColumn("Mean Weekly LMS Logins", format="%.2f"),
            "mean_assignment": st.column_config.NumberColumn("Mean Assignment Completion (%)", format="%.2f%%")
        }
    )
