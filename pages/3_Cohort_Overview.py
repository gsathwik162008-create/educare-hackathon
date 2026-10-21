"""
Smart Campus Analytics - Cohort Overview & Cross-Sectional Analysis
Role Guard: ADMIN only.
Faculty and Students attempting to access this page directly see a clear refusal message.
All metrics, matrix aggregations, and distributions are computed in core/score.py.
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px

from core.ui import load_css, render_kpi_card, render_insight_header
from core.score import (
    get_cohort_summary_kpis,
    get_department_year_heatmap,
    get_segment_distribution,
    get_top_triage_students,
    get_cohort_scores_distribution
)

# Load Institutional Design System
load_css()

# 1. Role Guard & Navigation Check
user = st.session_state.get("user")
if not st.session_state.get("authenticated") or not user:
    st.error("Authentication Required: Please log in on the main portal page.")
    st.stop()

role = user.get("role", "").upper()
if role != "ADMIN":
    st.error(f"Access Denied: Role '{role}' is not authorized to view the Institutional Cohort Overview.")
    st.info("Institutional Cohort Overview is strictly restricted to Academic Leadership and System Administrators.")
    st.stop()

# 2. Header & Title
st.title("Institutional Cohort Overview")
st.caption("Cross-sectional analytics, risk concentration, and behavioral segmentation across all enrolled students.")

# 3. Dynamic Insight Title computed from core/
kpi_data = get_cohort_summary_kpis()
render_insight_header(kpi_data["insight_sentence"])

# 4. KPI Cards
c1, c2, c3, c4, c5 = st.columns(5)
with c1:
    render_kpi_card(kpi_data["total_students"], "Total Students")
with c2:
    render_kpi_card(f"{kpi_data['mean_success_score']:.1f}", "Mean Success Score")
with c3:
    render_kpi_card(kpi_data["academic_risk_high_count"], "Academic Risk High")
with c4:
    render_kpi_card(kpi_data["placement_risk_high_count"], "Placement Risk High")
with c5:
    render_kpi_card(kpi_data["low_confidence_count"], "Low Data Confidence")

st.write("---")

# 5. Visualizations Section: Distribution Histogram & Department x Year Heatmap
col_vis1, col_vis2 = st.columns([1, 1])

with col_vis1:
    st.subheader("Success Score Distribution")
    scores_series = get_cohort_scores_distribution()
    
    # Histogram with thin bars, clean KPMG styling, no legend
    fig_hist = go.Figure()
    fig_hist.add_trace(go.Histogram(
        x=scores_series,
        nbinsx=35,
        marker=dict(
            color="#00338D",
            line=dict(color="#FFFFFF", width=0.8)
        ),
        showlegend=False
    ))
    fig_hist.update_layout(
        height=320,
        margin=dict(l=20, r=20, t=20, b=20),
        xaxis_title="Success Score (0 - 100)",
        yaxis_title="Student Count",
        paper_bgcolor="#FFFFFF",
        plot_bgcolor="#F8FAFD",
        showlegend=False
    )
    st.plotly_chart(fig_hist, use_container_width=True)

with col_vis2:
    st.subheader("Department × Year Mean Success Score")
    hm_data = get_department_year_heatmap()

    # Heatmap matrix with tight colour scale anchored to min/max cell means
    mean_vals = [val for row in hm_data["mean_matrix"] for val in row]
    z_min = min(mean_vals)
    z_max = max(mean_vals)

    fig_hm = go.Figure(data=go.Heatmap(
        z=hm_data["mean_matrix"],
        x=hm_data["years"],
        y=hm_data["departments"],
        zmin=z_min,
        zmax=z_max,
        colorscale=[
            [0.0, "#F2E2DF"],   # Soft light red/pink for cell minimum
            [0.5, "#E6F0FA"],   # Soft ice blue for cell midpoint
            [1.0, "#00338D"]    # Institutional deep navy for cell maximum
        ],
        text=hm_data["annotations"],
        texttemplate="%{text}",
        textfont=dict(color="#002244", size=12),
        showscale=False
    ))
    fig_hm.update_layout(
        height=320,
        margin=dict(l=20, r=20, t=20, b=20),
        xaxis_title="Academic Year",
        yaxis_title="Department",
        paper_bgcolor="#FFFFFF",
        plot_bgcolor="#F8FAFD"
    )
    st.plotly_chart(fig_hm, use_container_width=True)
    if hm_data["has_small_sample"]:
        st.caption("* Note: Cell marked with asterisk indicates sample size n < 15.")

st.write("---")

# 6. Rule-based Behavioral Segment Distribution
col_seg1, col_seg2 = st.columns([3, 2])

with col_seg1:
    st.subheader("Cohort Behavioral Segments")
    seg_df = get_segment_distribution()

    fig_seg = go.Figure(go.Bar(
        x=seg_df["count"],
        y=seg_df["segment"],
        orientation="h",
        marker=dict(color="#005EB8"),
        text=seg_df.apply(lambda r: f"{r['count']} ({r['percentage']}%)", axis=1),
        textposition="outside",
        showlegend=False
    ))
    fig_seg.update_layout(
        height=260,
        margin=dict(l=20, r=40, t=20, b=20),
        xaxis_title="Number of Students",
        yaxis=dict(autorange="reversed"),
        paper_bgcolor="#FFFFFF",
        plot_bgcolor="#F8FAFD"
    )
    st.plotly_chart(fig_seg, use_container_width=True)

with col_seg2:
    st.markdown("##### Segment Definitions (Rule-Based)")
    st.markdown(
        """
        - **Stars**: High academic standing (>=75) & high placement readiness (>=75).
        - **Steady Performers**: Balanced academic and placement engagement (scores >=50).
        - **High Academics / Low Placement**: Strong coursework, lagging certifications & coding.
        - **Disengaging**: Declining longitudinal attendance/LMS or recent GPA drop.
        - **Silent Strugglers**: Low academic health (<50) without high behavioral flags.
        """
    )

st.write("---")

# 7. Priority Triage: Top 10 by Risk Triage Score
st.subheader("Priority Intervention Roster (Top 10 by Risk Triage Score)")
st.caption("Sorted by composite faculty triage score combining success deficits, risk tiers, and negative trajectory deltas.")

top_students_df = get_top_triage_students(limit=10)

# Format table for display
display_df = top_students_df.copy()
display_df["Student Profile Link"] = display_df["student_id"].apply(
    lambda sid: f"Profile: {sid}"
)

# Reorder columns
table_cols = [
    "student_id", "name", "department", "year", "success_score",
    "risk_triage_score", "academic_risk", "placement_risk", "risk_reasons"
]
st.dataframe(
    display_df[table_cols],
    use_container_width=True,
    hide_index=True,
    column_config={
        "student_id": st.column_config.TextColumn("Student ID", help="Copy ID to navigate to Student Profile"),
        "name": "Student Name",
        "department": "Dept",
        "year": "Year",
        "success_score": st.column_config.NumberColumn("Success Score", format="%.1f"),
        "risk_triage_score": st.column_config.NumberColumn("Triage Score", format="%.1f"),
        "academic_risk": "Acad Risk",
        "placement_risk": "Place Risk",
        "risk_reasons": "Identified Risk Reasons"
    }
)
