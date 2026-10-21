"""Institutional data-quality audit view. Role Guard: ADMIN only."""

import plotly.graph_objects as go
import streamlit as st

from core.ingest import get_data_quality_summary
from core.ui import load_css, render_insight_header, render_kpi_card

load_css()

user = st.session_state.get("user")
if not st.session_state.get("authenticated") or not user:
    st.error("Authentication Required: Please log in on the main portal page.")
    st.stop()

role = user.get("role", "").upper()
if role != "ADMIN":
    st.error(f"Access Denied: Role '{role}' is not authorized to view Data Quality.")
    st.info("Data Quality is restricted to System Administrators.")
    st.stop()

st.title("Data Quality")
summary = get_data_quality_summary()
render_insight_header(summary["insight_title"])

kpi_columns = st.columns(4)
with kpi_columns[0]:
    render_kpi_card(f"{summary['total_fix_actions']:,}", "Total fix actions")
with kpi_columns[1]:
    render_kpi_card(summary["distinct_issue_types"], "Distinct issue types")
with kpi_columns[2]:
    render_kpi_card(f"{summary['duplicate_rows_removed']:,}", "Duplicate rows removed")
with kpi_columns[3]:
    imputation_value = (
        f"Missing: {summary['missing_values_imputed']:,}<br>"
        f"<span style='font-size: 1rem; font-weight: 600;'>"
        f"Invalid: {summary['invalid_values_imputed']:,}</span>"
    )
    render_kpi_card(imputation_value, "Values imputed (kept separate)")

st.write("---")
st.subheader("Rows affected by issue type")
issue_totals = summary["issue_totals"]
if issue_totals.empty:
    st.info("No cleaning-log entries are available.")
else:
    figure = go.Figure(go.Bar(
        x=issue_totals["rows_affected"],
        y=issue_totals["issue_type"],
        orientation="h",
        marker_color="#005EB8",
        showlegend=False,
        hovertemplate="%{y}<br>Rows affected: %{x:,}<extra></extra>",
    ))
    figure.update_layout(
        height=360,
        margin=dict(l=20, r=20, t=15, b=20),
        bargap=0.42,
        xaxis_title="Rows affected",
        yaxis=dict(autorange="reversed"),
        paper_bgcolor="#FFFFFF",
        plot_bgcolor="#F8FAFD",
        showlegend=False,
    )
    st.plotly_chart(figure, width="stretch")

st.write("---")
st.subheader("Main source row counts")
st.dataframe(
    summary["main_source_counts"],
    width="stretch",
    hide_index=True,
    column_config={
        "file": st.column_config.TextColumn("Source file"),
        "before_count": st.column_config.NumberColumn("Before", format="%d"),
        "after_count": st.column_config.NumberColumn("After", format="%d"),
    },
)

if summary["cgpa_caption"]:
    st.caption(summary["cgpa_caption"])
if summary["attendance_caption"]:
    st.caption(summary["attendance_caption"])

st.write("---")
st.subheader("Cleaning log")
st.dataframe(
    summary["log_entries"],
    width="stretch",
    hide_index=True,
    column_config={
        "file": st.column_config.TextColumn("File"),
        "issue_type": st.column_config.TextColumn("Issue type"),
        "rows_affected": st.column_config.NumberColumn("Rows affected", format="%d"),
        "before_count": st.column_config.NumberColumn("Before count", format="%d"),
        "after_count": st.column_config.NumberColumn("After count", format="%d"),
        "action": st.column_config.TextColumn("Action"),
    },
)