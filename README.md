# Smart Campus Analytics

An analytics-driven Student Success Platform built for the KPMG challenge at the Bytexl hackathon. It integrates seven student data sources into one unified view, computes a transparent Student Success Score, flags students who may need support, and converts the result into a ranked, trackable action list for mentors.

All data in this repository is synthetic. It was generated deliberately messy so that the cleaning and integration pipeline can be demonstrated end to end.

## What it does

| Capability | Where |
|---|---|
| Integrates 7 sources (academic, attendance, LMS, engagement, placement, skills, feedback) plus 4 history tables into one student record | `core/ingest.py` |
| Logs every cleaning action with before and after counts | `cleaning_log` table, Data Quality screen |
| Student Success Score with Academic Health and Placement Readiness sub-scores | `core/score.py` |
| Rule-based risk flags with stored reasons, plus per-student drivers | `core/score.py` |
| Intervention queue: action priority, owner, due date, status tracking | `core/interventions.py` |
| What-if simulator that re-scores a student from changed indicators | `core/score.py` (`score_student`) |
| Plain-English explanations (analyst tone for staff, supportive tone for students) | `core/explain.py` |
| Role-based access: Admin, Faculty (own mentees only), Student (own record only) | `core/auth.py` |

## Screens

| Screen | Roles | Purpose |
|---|---|---|
| Faculty Queue | Faculty, Admin | Mentees ranked by action priority, with status updates saved to the database |
| Student Profile | Faculty, Admin | Score, drivers, trends, subject table, explanation, what-if sliders |
| Cohort Overview | Admin | KPIs, department by year heatmap, segment mix, top triage list |
| Trends | Admin, Faculty (scoped) | CGPA, attendance and LMS trends, with a scan for department by year anomalies |
| Segments | Admin, Faculty (scoped) | Rule-based segments, 2x2 scatter, K-Means personas |
| Data Quality | Admin | Cleaning log summary, issue counts, before and after row counts |
| Student Portal | Student | Supportive view: progress, focus areas, next steps, what-if planner |

The Student Portal never shows risk labels, ranks, segment names or other students' data.

## Run it

Python 3.11 or newer is recommended. The project was developed on Python 3.14 `[CONFIRM: test on 3.11/3.12]`.

```bash
pip install -r requirements.txt
streamlit run app.py
```

The prepared database (`data/campus.db`) and user accounts (`data/users.csv`) are included, so no seeding is needed to run the demo.

To rebuild the data from scratch `[CONFIRM these commands on a fresh clone]`:

```bash
python scripts/seed.py
python -m core.ingest
python scripts/run_rescore.py
```

## Demo logins

| Role | Username | Password |
|---|---|---|
| Admin | `admin` | `Admin@2026` |
| Faculty | `FAC_CSE_01` | `Faculty@CSE1` |
| Faculty | `FAC_MECH_01` | `Faculty@MECH1` |
| Faculty | `FAC_CIVIL_01` | `Faculty@CIVIL1` |
| Student | `21CSE089` | `Student@21CSE089` |
| Student | `22ECE045` | `Student@22ECE045` |
| Student | `21MECH012` | `Student@21MECH012` |
| Student | `23CIVIL034` | `Student@23CIVIL034` |
| Student | `22EEE071` | `Student@22EEE071` |

These are demo-only credentials for synthetic accounts. Passwords are stored as bcrypt hashes.

## Repository layout

```
app.py                 login, role-based navigation
pages/                 the seven screens plus the home page
core/                  all logic: ingest, score, interventions, explain, auth, config
scripts/               seed script, verification scripts, role-guard test
data/                  raw CSVs, campus.db, users.csv
assets/style.css       KPMG-style theme
score_note.md          one-page note on the Success Score
```

## Verification scripts

```bash
python scripts/verify_phase3.py
python scripts/verify_phase4a.py
python scripts/verify_phase4b.py
python scripts/test_role_guards.py
python scripts/verify_student_portal.py
```

These check scoring, intervention logic, role scoping (including refusal of cross-student and cross-mentor access), write protection, and banned wording in the student portal. They modify the database (for example, one intervention status), so avoid running them right before a demo.

## Limitations

- Data is synthetic. Model signals trained on rule-based labels are circular and are not presented as accuracy claims.
- Intervention history and the effectiveness table are demo data and are labelled as such.
- The Success Score is a point-in-time composite. Trends use CGPA, attendance and LMS history only.
- Login state is held in the browser session and is lost on a page refresh.