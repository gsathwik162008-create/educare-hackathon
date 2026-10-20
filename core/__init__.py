"""Core package for Smart Campus Analytics."""

from core.auth import (
    authenticate_user,
    get_students_for_user,
    get_interventions_for_user,
    generate_users_csv
)
from core.ui import load_css, render_kpi_card, render_insight_header, render_demo_badge
