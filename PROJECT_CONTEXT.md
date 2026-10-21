Project: Smart Campus Analytics (KPMG challenge, Bytexl hackathon).
Stack: Python, Streamlit, pandas, scikit-learn, Plotly, SQLite.
No React/FastAPI/Docker.

Rules:
- All calculations live in core/, pages only call core functions.
- Weights/thresholds in core/config.py. DEMO_TODAY = 2026-10-20.
- Student-facing views never show risk labels, rank or segment names.
- Every function taking a student_id must check the user's scope.
- No emoji. Light KPMG theme (navy #00338D, blue #005EB8). Design in assets/style.css.
- Do one page per task. Show raw output, not summaries.

Done and verified: data pipeline (ingest, cleaning_log), scoring,
interventions, auth (3 roles), Faculty Queue, Student Profile,
Cohort Overview, Trends, Segments.
Tests that must keep passing: scripts/verify_phase3.py, verify_phase4a.py,
verify_phase4b.py, test_role_guards.py.
Key facts: 600 students, 16 mentors, 346 interventions, Aarav (21CSE089)
= score 38.1, Coding bootcamp, priority 11.53, +6.2.

Next: Student portal, Data Quality page, README, score_note.md, slides.