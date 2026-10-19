"""
Smart Campus Analytics - Configuration Module
Defines all database paths, weights, thresholds, mappings, and system constants.
"""

from pathlib import Path

# Paths
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
DB_PATH = DATA_DIR / "campus.db"

# Department standardisation mapping
DEPARTMENT_MAPPING = {
    "CSE": "CSE",
    "C.S.E": "CSE",
    "COMPUTER SCIENCE": "CSE",
    "ECE": "ECE",
    "E.C.E": "ECE",
    "ELECTRONICS": "ECE",
    "EEE": "EEE",
    "E.E.E": "EEE",
    "ELECTRICAL": "EEE",
    "MECH": "Mech",
    "MECHANICAL": "Mech",
    "CIVIL": "Civil",
    "C.I.V.I.L": "Civil"
}

# Standard Departments & Years
DEPARTMENTS = ["CSE", "ECE", "EEE", "Mech", "Civil"]
YEARS = [1, 2, 3, 4]

# Success Score Indicator Weights (Total = 1.0)
WEIGHTS = {
    "academic": 0.35,        # CGPA and backlogs
    "attendance": 0.20,      # Overall attendance percentage
    "placement": 0.20,       # Coding, aptitude, mock interviews
    "lms_engagement": 0.15,  # LMS logins, assignment completion, events
    "skills_feedback": 0.10  # Certifications, technical/softskill, faculty rating
}

# Sub-weights for indicator breakdowns
SUB_WEIGHTS = {
    "cgpa": 0.25,
    "backlogs_inv": 0.10,
    "attendance_pct": 0.20,
    "coding": 0.08,
    "aptitude": 0.07,
    "mock_interviews": 0.05,
    "assignment_completion_pct": 0.06,
    "lms_logins_avg": 0.05,
    "engagement_score": 0.04,
    "skills_score": 0.06,
    "feedback_score": 0.04
}

# Risk Thresholds
THRESHOLDS = {
    "cgpa_min": 6.0,
    "attendance_min": 75.0,
    "backlogs_max": 2,
    "coding_min": 40.0,
    "aptitude_min": 50.0,
    "trend_delta_warning": -5.0,
    "high_risk_score": 50.0,
    "medium_risk_score": 70.0
}

# Rule-based Segment Labels
SEGMENTS = {
    "STARS": "Stars",
    "HIGH_ACAD_LOW_PLACE": "High academics / low placement readiness",
    "SILENT_STRUGGLERS": "Silent strugglers",
    "DISENGAGING": "Disengaging",
    "STEADY": "Steady performers"
}

# Key Driver Indicators and their relative weights in Success Score
DRIVER_INDICATORS = {
    "cgpa_norm": ("CGPA", 0.25),
    "backlogs_norm": ("Backlog clearance", 0.10),
    "attendance_pct": ("Attendance", 0.20),
    "coding": ("Coding proficiency", 0.08),
    "aptitude": ("Aptitude score", 0.07),
    "mock_interviews_norm": ("Mock interviews", 0.05),
    "lms_logins_norm": ("LMS activity", 0.05),
    "assignment_completion_pct": ("Assignment completion", 0.06),
    "technical_score": ("Technical knowledge", 0.06),
    "softskill_score": ("Soft skills", 0.04),
    "feedback_norm": ("Faculty engagement", 0.04)
}

# Data Normalisation Ranges
VALUE_BOUNDS = {
    "cgpa": (0.0, 10.0),
    "backlogs": (0, 20),
    "attendance_pct": (0.0, 100.0),
    "lms_logins_avg": (0.0, 50.0),
    "assignment_completion_pct": (0.0, 100.0),
    "aptitude": (0.0, 100.0),
    "coding": (0.0, 100.0),
    "mock_interviews": (0, 10),
    "technical_score": (0.0, 100.0),
    "softskill_score": (0.0, 100.0),
    "satisfaction": (1.0, 5.0),
    "faculty_rating": (1.0, 5.0),
    "events": (0, 30),
    "clubs": (0, 10),
    "hackathons": (0, 15),
    "certifications": (0, 15),
    "marks": (0.0, 100.0)
}

# Target roles and required benchmarks for placement skill gap analysis
ROLE_REQUIREMENTS = {
    "Software Engineer": {"coding": 75, "aptitude": 70, "technical_score": 75},
    "Data Analyst": {"coding": 60, "aptitude": 75, "technical_score": 70},
    "Core Engineer": {"coding": 45, "aptitude": 65, "technical_score": 80},
    "Consultant / Business Analyst": {"coding": 40, "aptitude": 80, "technical_score": 65}
}
