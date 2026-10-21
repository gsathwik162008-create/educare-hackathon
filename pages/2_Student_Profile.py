"""
Smart Campus Analytics - Student Profile & Diagnostic Deep-Dive
Role Guard: FACULTY and ADMIN only.
Allows faculty and administrators to inspect comprehensive individual student metrics,
historical trends, driver indicators, and test simulated outcome improvements.
"""

import streamlit as st
import pandas as pd
import numpy as np
import sqlite3
import plotly.graph_objects as go
import plotly.express as px

from core.config import DB_PATH
from core.auth import get_students_for_user, get_student_by_id_scoped
from core.explain import explain_for_faculty, get_enhanced_explanation
from core.score import score_student
from core.ui import load_css, render_kpi_card, render_insight_header, render_demo_badge

# Load Institutional Design System
load_css()

# 1. Role Guard
user = st.session_state.get("user")
if not st.session_state.get("authenticated") or not user:
    st.error("Authentication Required: Please log in on the main portal page.")
    st.stop()

role = user.get("role", "").upper()
if role not in ["FACULTY", "ADMIN"]:
    st.error(f"Access Denied: Role '{role}' is not authorized to view Student Diagnostic Profiles.")
    st.stop()

# 2. Scoped Student Selection
conn = sqlite3.connect(DB_PATH)
scoped_students_df = get_students_for_user(user, table_name="students_scored", conn=conn)

if scoped_students_df.empty:
    conn.close()
    st.info("No students found in your authorized advisory scope.")
    st.stop()

# Build student picker choices
student_options = scoped_students_df.apply(
    lambda r: f"{r['name']} ({r['student_id']}) - {r['department']} Yr {int(r['year'])}",
    axis=1
).tolist()

# Student Selector in Top Header
top_c1, top_c2 = st.columns([3, 1])
with top_c1:
    selected_choice = st.selectbox(
        "Select Mentee from Scope",
        options=student_options,
        index=0,
        help="Only students assigned to your faculty scope are selectable."
    )
    selected_sid = selected_choice.split("(")[1].split(")")[0]

with top_c2:
    st.write("")
    st.write("")
    render_demo_badge()

# Load full detail using get_student_by_id_scoped (strict security verification)
try:
    student = get_student_by_id_scoped(selected_sid, user, conn=conn)
except PermissionError as pe:
    conn.close()
    st.error(str(pe))
    st.stop()

# 3. Dynamic Insight Header (No Emoji, Institutional Design)
score_val = float(student.get("success_score", 0.0))
acad_val = float(student.get("academic_health", 0.0))
place_val = float(student.get("placement_readiness", 0.0))
acad_risk = student.get("academic_risk", "Low")
place_risk = student.get("placement_risk", "Low")
conf_val = float(student.get("data_confidence", 100.0))
is_low_conf = int(student.get("low_confidence", 0)) == 1 or int(student.get("imputed_field_count", 0)) >= 3

insight_text = (
    f"Performance Diagnostic: {student['name']} ({student['student_id']}) | "
    f"Department of {student['department']} (Year {int(student['year'])}) | "
    f"Advisor: {student['mentor_id']}. "
    f"Overall composite score is {score_val:.1f}/100 with {acad_risk} academic risk and {place_risk} placement risk."
)
render_insight_header(insight_text)

# Low data confidence warning badge if applicable
if is_low_conf:
    st.markdown(
        f'<div class="demo-badge" style="border-color: #B5412F; color: #B5412F; background-color: #FFF5F5;">'
        f'LOW DATA CONFIDENCE — {int(student.get("imputed_field_count", 0))} FIELDS IMPUTED ({conf_val:.1f}% CONFIDENCE)'
        f'</div>',
        unsafe_allow_html=True
    )

# 4. Top KPI Cards & Score Breakdown
k1, k2, k3, k4, k5 = st.columns(5)
with k1:
    render_kpi_card(f"{score_val:.1f}", "Success Score")
with k2:
    render_kpi_card(f"{acad_val:.1f}", "Academic Health")
with k3:
    render_kpi_card(f"{place_val:.1f}", "Placement Readiness")
with k4:
    render_kpi_card(f"{float(student.get('cgpa', 0.0)):.2f}", f"CGPA ({int(student.get('backlogs', 0))} Backlogs)")
with k5:
    render_kpi_card(f"{float(student.get('attendance_pct', 0.0)):.1f}%", "Attendance Rate")

# 5. Core Performance Gauges & Driver Indicators
st.write("---")
g_col, d_col = st.columns([1, 1])

with g_col:
    st.subheader("Performance Health Gauges")
    # Plotly bullet/gauge chart for Success Score, Academic Health, and Placement Readiness
    fig_gauge = go.Figure()

    fig_gauge.add_trace(go.Indicator(
        mode="gauge+number",
        value=score_val,
        domain={'x': [0, 1], 'y': [0.55, 1]},
        title={'text': "Composite Success Score", 'font': {'size': 14, 'color': '#00338D'}},
        gauge={
            'axis': {'range': [0, 100], 'tickwidth': 1, 'tickcolor': "#DDE3EC"},
            'bar': {'color': "#00338D"},
            'steps': [
                {'range': [0, 50], 'color': "#FDE8E8"},
                {'range': [50, 70], 'color': "#FEF3C7"},
                {'range': [70, 100], 'color': "#DEF7EC"}
            ],
            'threshold': {
                'line': {'color': "#B5412F", 'width': 3},
                'thickness': 0.75,
                'value': 50
            }
        }
    ))

    fig_gauge.update_layout(
        height=260,
        margin=dict(l=20, r=20, t=30, b=10),
        paper_bgcolor="#FFFFFF",
        font=dict(color="#1F2933", family="sans serif")
    )
    st.plotly_chart(fig_gauge, use_container_width=True)

with d_col:
    st.subheader("Indicator Driver Attribution")
    st.caption("Contribution of individual metrics to departure from cohort benchmarks (+pts impact).")
    
    # Parse drivers or re-evaluate drivers for visual bars
    drags_text = student.get("top_drags", "None")
    strengths_text = student.get("top_strengths", "None")
    
    # Render driver metrics cleanly
    st.markdown(f"**Key Headwinds (Top Negative Drags):**")
    if drags_text and drags_text != "None":
        for item in drags_text.split(", "):
            st.markdown(f"- <span class='risk-high'>•</span> {item}", unsafe_allow_html=True)
    else:
        st.markdown("- None identified.")

    st.markdown(f"**Key Tailwinds (Top Strengths):**")
    if strengths_text and strengths_text != "None":
        for item in strengths_text.split(", "):
            st.markdown(f"- <span class='risk-green'>•</span> {item}", unsafe_allow_html=True)
    else:
        st.markdown("- None identified.")

    st.markdown(f"**Identified Risk Flags:**")
    st.info(student.get("risk_reasons", "Normal academic & placement standing"))

    ew_prob = float(student.get("early_warning_prob", 0.0))
    if ew_prob >= 0.70:
        sig_tier = "High"
        sig_class = "risk-high"
    elif ew_prob >= 0.35:
        sig_tier = "Medium"
        sig_class = "risk-amber"
    else:
        sig_tier = "Low"
        sig_class = "risk-green"

    st.markdown(
        f"Early Warning: <span class='{sig_class}'><strong>{sig_tier}</strong></span> model signal "
        f"<span style='color: #68737D; font-size: 0.85rem;'>(trained on rule flags)</span>",
        unsafe_allow_html=True
    )

# 6. Longitudinal History: Trends & Semester Trajectory
st.write("---")
st.subheader("Longitudinal Analytics & Historical Trends")

t_col1, t_col2 = st.columns(2)

with t_col1:
    st.markdown("##### Semester CGPA Trajectory")
    sem_history_df = pd.read_sql(
        "SELECT semester, sgpa, cgpa, backlogs FROM semester_history WHERE student_id = ? ORDER BY semester",
        conn,
        params=(selected_sid,)
    )
    if not sem_history_df.empty:
        fig_sem = go.Figure()
        fig_sem.add_trace(go.Scatter(
            x=sem_history_df["semester"],
            y=sem_history_df["cgpa"],
            mode="lines+markers",
            name="Cumulative CGPA",
            line=dict(color="#00338D", width=3)
        ))
        fig_sem.add_trace(go.Scatter(
            x=sem_history_df["semester"],
            y=sem_history_df["sgpa"],
            mode="lines+markers",
            name="Semester SGPA",
            line=dict(color="#005EB8", width=2, dash="dash")
        ))
        fig_sem.update_layout(
            height=260,
            margin=dict(l=20, r=20, t=20, b=20),
            xaxis_title="Semester",
            yaxis_title="Grade Point Average",
            paper_bgcolor="#FFFFFF",
            plot_bgcolor="#F8FAFD",
            legend=dict(orientation="h", y=1.1, x=0.5, xanchor="center")
        )
        st.plotly_chart(fig_sem, use_container_width=True)
    else:
        st.caption("No semester history on record.")

with t_col2:
    st.markdown("##### Monthly Attendance Trend")
    att_history_df = pd.read_sql(
        "SELECT month, attendance_pct FROM attendance_history WHERE student_id = ? ORDER BY month",
        conn,
        params=(selected_sid,)
    )
    if not att_history_df.empty:
        fig_att = go.Figure()
        fig_att.add_trace(go.Scatter(
            x=att_history_df["month"],
            y=att_history_df["attendance_pct"],
            mode="lines+markers",
            name="Attendance %",
            line=dict(color="#4C7A4F", width=2.5)
        ))
        fig_att.update_layout(
            height=260,
            margin=dict(l=20, r=20, t=20, b=20),
            paper_bgcolor="#FFFFFF",
            plot_bgcolor="#F8FAFD",
            xaxis_title="Month",
            yaxis=dict(title="Attendance Rate (%)", range=[0, 100]),
            showlegend=False
        )
        st.plotly_chart(fig_att, use_container_width=True)
    else:
        st.caption("No attendance history on record.")

# Separate LMS Weekly Activity Chart (No Legend Overlap)
st.markdown("##### Weekly LMS Engagement & Assignment Submissions")
lms_history_df = pd.read_sql(
    "SELECT week, logins, assignments_completed FROM lms_history WHERE student_id = ? ORDER BY week",
    conn,
    params=(selected_sid,)
)
if not lms_history_df.empty:
    fig_lms = go.Figure()
    fig_lms.add_trace(go.Bar(
        x=lms_history_df["week"],
        y=lms_history_df["logins"],
        name="LMS Weekly Logins",
        marker_color="#005EB8"
    ))
    fig_lms.add_trace(go.Scatter(
        x=lms_history_df["week"],
        y=lms_history_df["assignments_completed"],
        mode="lines+markers",
        name="Assignments Completed",
        line=dict(color="#C9922E", width=2.5),
        yaxis="y2"
    ))
    fig_lms.update_layout(
        height=260,
        margin=dict(l=20, r=20, t=20, b=20),
        paper_bgcolor="#FFFFFF",
        plot_bgcolor="#F8FAFD",
        xaxis_title="Course Week",
        yaxis=dict(title="LMS Logins", range=[0, max(15, lms_history_df["logins"].max() + 2)]),
        yaxis2=dict(title="Assignments Completed", overlaying="y", side="right", range=[0, 5]),
        legend=dict(orientation="h", y=1.1, x=0.5, xanchor="center")
    )
    st.plotly_chart(fig_lms, use_container_width=True)
else:
    st.caption("No LMS activity history on record.")

# 7. Subject-wise Marks and Attendance Table
st.write("---")
st.subheader("Subject-wise Coursework & Attendance Breakdown")
subjects_df = pd.read_sql(
    "SELECT subject_code, subject_name, semester, marks, attendance FROM subject_marks WHERE student_id = ? ORDER BY semester DESC, subject_code",
    conn,
    params=(selected_sid,)
)

if not subjects_df.empty:
    sub_view = subjects_df.copy()
    sub_view.columns = ["Course Code", "Subject Name", "Semester", "Marks (%)", "Attendance (%)"]
    st.dataframe(
        sub_view,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Semester": st.column_config.NumberColumn(format="Sem %d"),
            "Marks (%)": st.column_config.NumberColumn(format="%.1f%%"),
            "Attendance (%)": st.column_config.NumberColumn(format="%.1f%%"),
        }
    )
else:
    st.caption("No subject-level coursework records found.")

# 8. Faculty Narrative Explanation
st.write("---")
st.subheader("Advisory Explanation Narrative")
template_narrative = explain_for_faculty(student)
st.markdown(f"""
<div class="panel-card" style="border-left: 4px solid #00338D; margin-bottom: 12px;">
    <div style="font-weight: 600; color: #00338D; margin-bottom: 6px;">Quantitative Risk Profile & Action Plan (Template Benchmark)</div>
    <div style="font-size: 0.95rem; line-height: 1.6; color: #1F2933;">
        {template_narrative}
    </div>
</div>
""", unsafe_allow_html=True)

# Optional LLM qualitative text if validated
qualitative_text = get_enhanced_explanation(selected_sid, role="faculty", student_dict=student)
if qualitative_text and qualitative_text != template_narrative:
    with st.expander("Qualitative Advisory Synthesis (LLM Context)", expanded=False):
        st.markdown(f"""
        <div style="font-size: 0.92rem; line-height: 1.6; color: #1F2933;">
            {qualitative_text}
        </div>
        """, unsafe_allow_html=True)

# 9. What-If Scenario Simulator
st.write("---")
st.subheader("What-If Scenario Simulator (Simulated & Estimated)")
st.caption("Adjust key metrics to simulate score trajectory and determine the highest-leverage growth path. Results are labeled as estimated and simulated.")

sim_col1, sim_col2 = st.columns([1, 1])

with sim_col1:
    st.markdown("##### Adjust Student Input Levers")
    curr_att = int(round(float(student.get("attendance_pct", 75.0))))
    curr_code = int(round(float(student.get("coding", 50.0))))
    curr_back = int(round(float(student.get("backlogs", 0))))
    curr_mock = int(round(float(student.get("mock_interviews", 0))))
    curr_lms = int(round(float(student.get("assignment_completion_pct", 70.0))))

    sim_att = st.slider("Attendance Rate (%)", min_value=0, max_value=100, value=curr_att, step=1, format="%d%%")
    sim_code = st.slider("Coding Proficiency Score (0-100)", min_value=0, max_value=100, value=curr_code, step=1, format="%d")
    sim_back = st.slider("Active Backlog Count", min_value=0, max_value=10, value=curr_back, step=1, format="%d")
    sim_mock = st.slider("Completed Mock Interviews", min_value=0, max_value=5, value=curr_mock, step=1, format="%d")
    sim_lms = st.slider("Assignment Completion Rate (%)", min_value=0, max_value=100, value=curr_lms, step=1, format="%d%%")

with sim_col2:
    st.markdown("##### Simulated Outcome Projections")
    
    # Build simulated indicator payload
    sim_payload = dict(student)
    sim_payload["attendance_pct"] = sim_att
    sim_payload["coding"] = sim_code
    sim_payload["backlogs"] = sim_back
    sim_payload["mock_interviews"] = sim_mock
    sim_payload["assignment_completion_pct"] = sim_lms

    sim_result = score_student(sim_payload)
    new_score = sim_result["success_score"]
    delta_score = round(new_score - score_val, 1)

    # Determine highest-impact lever
    levers = [
        ("Coding Practice", round((sim_code - curr_code) * 0.08, 1)),
        ("Attendance Attendance", round((sim_att - curr_att) * 0.20, 1)),
        ("Backlog Clearance", round((curr_back - sim_back) * 2.0, 1)),
        ("Mock Interviews", round((sim_mock - curr_mock) * 1.25, 1)),
        ("Assignment Completion", round((sim_lms - curr_lms) * 0.06, 1))
    ]
    levers.sort(key=lambda x: x[1], reverse=True)
    biggest_lever_name, biggest_lever_impact = levers[0]
    biggest_lever_str = f"{biggest_lever_name} ({biggest_lever_impact:+.1f} pts)" if biggest_lever_impact != 0 else "Baseline parameters unchanged"

    sc1, sc2, sc3 = st.columns(3)
    with sc1:
        render_kpi_card(f"{score_val:.1f}", "Current Score")
    with sc2:
        render_kpi_card(f"{new_score:.1f}", "Simulated Score")
    with sc3:
        sign = "+" if delta_score >= 0 else ""
        render_kpi_card(f"{sign}{delta_score:.1f}", "Estimated Delta")

    st.markdown(f"""
    <div class="panel-card" style="margin-top: 12px; background-color: #F8FAFD;">
        <div style="font-weight: 600; color: #00338D; margin-bottom: 4px;">Primary Growth Lever</div>
        <div style="font-size: 0.95rem; color: #1F2933;">{biggest_lever_str}</div>
        <div style="font-size: 0.75rem; color: #68737D; margin-top: 6px; font-variant: small-caps;">
            Estimated, simulated trajectory projection based on multi-indicator weighting.
        </div>
    </div>
    """, unsafe_allow_html=True)

conn.close()
