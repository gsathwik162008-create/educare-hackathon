"""
Smart Campus Analytics - Behavioral Segments & Personas
Role Guard: ADMIN and FACULTY.
- ADMIN views the full institutional cohort.
- FACULTY views strictly their own advisory mentees (scoped via core.auth.get_students_for_user).
- STUDENT is denied access. Segment names are never shown in student-facing views.
All segment rules, K-Means personas, and aggregations are computed in core/score.py.
"""

import streamlit as st
import plotly.graph_objects as go

from core.ui import load_css, render_insight_header
from core.auth import get_students_for_user
from core.score import get_segments_analytics

load_css()

user = st.session_state.get("user")
if not st.session_state.get("authenticated") or not user:
    st.error("Authentication Required: Please log in on the main portal page.")
    st.stop()

role = user.get("role", "").upper()
if role not in ["ADMIN", "FACULTY"]:
    st.error(f"Access Denied: Role '{role}' is not authorized to view Behavioral Segments.")
    st.stop()

scoped_df = get_students_for_user(user, table_name="students_scored")
if scoped_df.empty:
    st.info("No student records available within your assigned scope.")
    st.stop()

analytics = get_segments_analytics(scoped_df)

st.title("Behavioral Segments")
scope_label = (
    "Institutional Population (All Departments)"
    if role == "ADMIN"
    else f"Faculty Advisory Scope ({analytics['total']} Mentees)"
)
st.caption(
    "Rule-based intervention groups and K-Means personas for faculty and academic leadership. "
    f"Scope: {scope_label}. Segment names are withheld from student-facing views."
)

render_insight_header(analytics["insight_title"])

rule_table = analytics["rule_table"]
st.subheader("Rule-Based Segments")
st.caption("Each row is one mutually exclusive rule, with mean indicators and a single action from the intervention library.")

if not rule_table.empty:
    display_rules = rule_table.copy()
    st.dataframe(
        display_rules,
        use_container_width=True,
        hide_index=True,
        column_config={
            "segment": st.column_config.TextColumn("Segment"),
            "rule": st.column_config.TextColumn("Rule (plain language)"),
            "count": st.column_config.NumberColumn("Students (n)", format="%d"),
            "share_pct": st.column_config.NumberColumn("Share (%)", format="%.1f"),
            "mean_success_score": st.column_config.NumberColumn("Mean score", format="%.1f"),
            "mean_academic_health": st.column_config.NumberColumn("Mean academic health", format="%.1f"),
            "mean_placement_readiness": st.column_config.NumberColumn("Mean placement readiness", format="%.1f"),
            "mean_attendance_pct": st.column_config.NumberColumn("Mean attendance (%)", format="%.1f"),
            "recommended_action": st.column_config.TextColumn("Recommended action"),
        },
    )
else:
    st.info("No rule segments available for this scope.")

st.write("---")

st.subheader("Academic Health vs Placement Readiness")
st.caption("One point per student. Colour encodes the rule segment (blue palette). Threshold lines mark academic health 70 and placement readiness 50. Labels sit at each segment centroid.")

scatter_traces = analytics["scatter_traces"]
scatter_ranges = analytics["scatter_ranges"]
thresholds = analytics["thresholds"]

if not scatter_traces:
    st.info("No scatter points available.")
else:
    fig = go.Figure()
    for trace in scatter_traces:
        fig.add_trace(go.Scatter(
            x=trace["x"],
            y=trace["y"],
            mode="markers",
            name=trace["segment"],
            marker=dict(size=7, color=trace["color"], opacity=0.75, line=dict(width=0)),
            hovertemplate=(
                "%{text}<br>Academic health: %{x:.1f}<br>Placement readiness: %{y:.1f}<extra></extra>"
            ),
            text=trace["student_ids"],
            showlegend=False,
        ))
        fig.add_annotation(
            x=trace["centroid_x"],
            y=trace["centroid_y"],
            text=trace["segment"],
            showarrow=False,
            font=dict(size=11, color=trace["color"]),
            bgcolor="rgba(255,255,255,0.75)",
            xanchor="center",
            yanchor="bottom",
        )

    x_line = thresholds["academic_health"]
    y_line = thresholds["placement_readiness"]
    x_min, x_max = scatter_ranges["academic_health"]
    y_min, y_max = scatter_ranges["placement_readiness"]

    fig.add_shape(
        type="line", x0=x_line, x1=x_line, y0=y_min, y1=y_max,
        line=dict(color="#68737D", width=1, dash="dash"),
    )
    fig.add_shape(
        type="line", x0=x_min, x1=x_max, y0=y_line, y1=y_line,
        line=dict(color="#68737D", width=1, dash="dash"),
    )

    fig.update_layout(
        height=420,
        margin=dict(l=20, r=20, t=20, b=20),
        xaxis=dict(title="Academic health", range=[x_min, x_max]),
        yaxis=dict(title="Placement readiness", range=[y_min, y_max]),
        paper_bgcolor="#FFFFFF",
        plot_bgcolor="#F8FAFD",
        showlegend=False,
    )
    st.plotly_chart(fig, use_container_width=True)

st.write("---")

st.subheader("K-Means Personas")
st.caption("Four statistical clusters labelled from centroid traits, not numbered cluster IDs. Cross-tab shows whether personas add information beyond the rule segments.")

cluster_table = analytics["cluster_table"]
if cluster_table.empty:
    st.info("Not enough students in scope to fit personas.")
else:
    st.dataframe(
        cluster_table,
        use_container_width=True,
        hide_index=True,
        column_config={
            "persona": st.column_config.TextColumn("Persona (from centroid)"),
            "n": st.column_config.NumberColumn("Students (n)", format="%d"),
            "mean_academic_health": st.column_config.NumberColumn("Mean academic health", format="%.1f"),
            "mean_placement_readiness": st.column_config.NumberColumn("Mean placement readiness", format="%.1f"),
            "mean_attendance_pct": st.column_config.NumberColumn("Mean attendance (%)", format="%.1f"),
            "mean_lms_logins": st.column_config.NumberColumn("Mean LMS logins", format="%.1f"),
            "mean_success_score": st.column_config.NumberColumn("Mean score", format="%.1f"),
        },
    )

    st.markdown("##### Centroids (original units)")
    st.dataframe(analytics["centroids"], use_container_width=True, hide_index=True)

    st.markdown("##### Persona vs rule segment")
    st.dataframe(analytics["cross_tab"], use_container_width=True)

st.write("---")

st.subheader("Segment Drill-Down")
st.caption("Scoped roster only, sorted by risk triage score. Top drag is the largest negative indicator driver.")

segment_options = analytics["segment_options"]
if not segment_options:
    st.info("No segments available to inspect.")
else:
    selected_segment = st.selectbox("Select a rule segment", options=segment_options)
    subset = analytics["drill_by_segment"][selected_segment]
    st.dataframe(
        subset,
        use_container_width=True,
        hide_index=True,
        column_config={
            "student_id": st.column_config.TextColumn("Student ID"),
            "name": st.column_config.TextColumn("Name"),
            "success_score": st.column_config.NumberColumn("Score", format="%.1f"),
            "top_drag": st.column_config.TextColumn("Top drag"),
            "risk_triage_score": st.column_config.NumberColumn("Risk triage score", format="%.1f"),
        },
    )
    st.caption(f"{analytics['drill_counts'][selected_segment]} students in this segment within the current scope.")
