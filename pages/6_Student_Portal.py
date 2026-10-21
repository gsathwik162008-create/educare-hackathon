"""Student-facing portal with strict account-only data access."""

import plotly.graph_objects as go
import streamlit as st

from core.auth import get_student_by_id_scoped
from core.config import VALUE_BOUNDS
from core.score import get_student_portal_data, score_student_portal_scenario
from core.ui import load_css

load_css()

user = st.session_state.get("user")
if not st.session_state.get("authenticated") or not user:
    st.error("Authentication required. Please sign in to continue.")
    st.stop()

if str(user.get("role", "")).upper() != "STUDENT":
    st.error("Access denied. This portal is available only to student accounts.")
    st.stop()

student_id = user.get("student_id") or user.get("username")
if not student_id:
    st.error("Your student account is missing its student ID.")
    st.stop()

try:
    portal = get_student_portal_data(student_id, user)
    student = get_student_by_id_scoped(student_id, user)
except PermissionError as exc:
    st.error(str(exc))
    st.stop()

st.title("My Student Portal")
st.caption(f"{student['name']} | {student['department']} | Year {int(student['year'])}")

progress_tab, focus_tab, subjects_tab, planner_tab, steps_tab = st.tabs(
    ["My progress", "Strengths and focus areas", "My subjects", "What-if planner", "My next steps"]
)

with progress_tab:
    st.header("My progress")
    score_col, cohort_col = st.columns(2)
    with score_col:
        st.metric(
            "My success score",
            f"{float(student['success_score']):.1f} / 100",
            delta=f"{portal['score_vs_cohort_average']:+.1f} vs cohort average",
            delta_color="off",
        )
    with cohort_col:
        st.metric("Cohort average", f"{portal['cohort_average_score']:.1f} / 100")
    st.caption("The comparison is with the cohort average, not with individual students.")

    history = portal["semester_history"]
    st.subheader("Semester CGPA")
    if history.empty:
        st.info("No semester record is available yet.")
    else:
        figure = go.Figure()
        figure.add_trace(go.Scatter(
            x=history["semester"],
            y=history["cgpa"],
            mode="lines+markers",
            name="Your cumulative CGPA",
            line={"color": "#00338D", "width": 3},
        ))
        figure.add_trace(go.Scatter(
            x=history["semester"],
            y=history["cohort_average_cgpa"],
            mode="lines+markers",
            name="Cohort average CGPA",
            line={"color": "#005EB8", "width": 2, "dash": "dash"},
        ))
        figure.update_layout(
            height=360,
            margin={"l": 20, "r": 20, "t": 20, "b": 20},
            xaxis_title="Semester",
            yaxis_title="Cumulative CGPA",
            yaxis={"range": [0, 10]},
            paper_bgcolor="#FFFFFF",
            plot_bgcolor="#F8FAFD",
            legend={"orientation": "h", "y": 1.1, "x": 0.5, "xanchor": "center"},
        )
        st.plotly_chart(figure, width="stretch")

with focus_tab:
    st.header("Strengths and focus areas")
    st.markdown(
        f"<div style='font-size: 1.15rem; line-height: 1.75; color: #1F2933;'>"
        f"{portal['supportive_text']}</div>",
        unsafe_allow_html=True,
    )

with subjects_tab:
    st.header("My subjects")
    subjects = portal["subject_marks"]
    if subjects.empty:
        st.info("No subject marks or attendance are available yet.")
    else:
        subjects = subjects.rename(columns={
            "subject_code": "Subject code",
            "subject_name": "Subject",
            "semester": "Semester",
            "marks": "Marks (%)",
            "attendance": "Attendance (%)",
        })
        st.dataframe(
            subjects,
            width="stretch",
            hide_index=True,
            column_config={
                "Semester": st.column_config.NumberColumn(format="%d"),
                "Marks (%)": st.column_config.NumberColumn(format="%.1f%%"),
                "Attendance (%)": st.column_config.NumberColumn(format="%.1f%%"),
            },
        )

with planner_tab:
    st.header("What-if planner")
    st.caption("Explore estimated, simulated outcomes. These are not changes to your record.")
    slider_values = {}
    slider_specs = [
        ("attendance_pct", "Attendance (%)"),
        ("coding", "Coding score"),
        ("backlogs", "Active backlogs"),
        ("mock_interviews", "Mock interviews completed"),
        ("assignment_completion_pct", "Assignment completion (%)"),
    ]
    slider_columns = st.columns(2)
    for index, (metric, label) in enumerate(slider_specs):
        minimum, maximum = VALUE_BOUNDS[metric]
        value = int(round(float(student.get(metric, minimum))))
        value = max(int(minimum), min(int(maximum), value))
        with slider_columns[index % 2]:
            slider_values[metric] = st.slider(
                label,
                min_value=int(minimum),
                max_value=int(maximum),
                value=value,
                step=1,
                format="%d",
                key=f"portal_{metric}",
            )

    estimate = score_student_portal_scenario(student_id, user, slider_values)
    result_cols = st.columns(3)
    with result_cols[0]:
        st.metric("Current score", f"{estimate['current_score']:.1f}")
    with result_cols[1]:
        st.metric("Simulated score", f"{estimate['simulated_score']:.1f}")
    with result_cols[2]:
        st.metric("Estimated change", f"{estimate['estimated_delta']:+.1f}")

with steps_tab:
    st.header("My next steps")
    steps = portal["next_steps"]
    if steps.empty:
        st.info("There are no next steps to show right now.")
    else:
        steps = steps.rename(columns={
            "action": "Next step",
            "description": "Details",
            "status": "Status",
            "due_date": "Due date",
            "source": "Assigned by",
        })
        st.dataframe(steps, width="stretch", hide_index=True)