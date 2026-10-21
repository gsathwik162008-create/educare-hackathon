"""
Smart Campus Analytics - Data Seeding Script
Generates 7 raw CSV sources and 4 time-series CSVs with realistic correlations,
deliberate anomalies (messy IDs, department aliases, missing values, duplicates,
out-of-range values), and 8 engineered test students (5 at-risk, 3 stars).
"""

import os
import random
import numpy as np
import pandas as pd
from pathlib import Path

# Set random seeds for reproducibility
np.random.seed(42)
random.seed(42)

BASE_DIR = Path(__file__).resolve().parent.parent
RAW_DIR = BASE_DIR / "data" / "raw"
RAW_DIR.mkdir(parents=True, exist_ok=True)

NUM_STUDENTS = 600
DEPTS = ["CSE", "ECE", "EEE", "Mech", "Civil"]
YEARS = [1, 2, 3, 4]

FIRST_NAMES = [
    "Aarav", "Aditi", "Rohan", "Pooja", "Rahul", "Sneha", "Vikram", "Ananya",
    "Aditya", "Priya", "Arjun", "Kavya", "Siddharth", "Neha", "Karthik", "Divya",
    "Varun", "Isha", "Manish", "Tanvi", "Suresh", "Meera", "Gaurav", "Swati",
    "Nikhil", "Shreya", "Harish", "Rhea", "Akash", "Deepika", "Kiran", "Nandini"
]

LAST_NAMES = [
    "Sharma", "Patel", "Verma", "Rao", "Iyer", "Deshmukh", "Kulkarni", "Singh",
    "Joshi", "Nair", "Reddy", "Choudhury", "Gupta", "Menon", "Bhat", "Pillai",
    "Kumar", "Mehta", "Das", "Banerjee", "Chatterjee", "Mishra", "Patil", "Natarajan"
]

SUBJECTS_BY_DEPT = {
    "CSE": [
        ("CS101", "Data Structures"),
        ("CS102", "Algorithms"),
        ("CS103", "Operating Systems"),
        ("CS104", "Database Management"),
        ("CS105", "Computer Networks")
    ],
    "ECE": [
        ("EC101", "Signals and Systems"),
        ("EC102", "Digital Electronics"),
        ("EC103", "Microprocessors"),
        ("EC104", "Analog Circuits"),
        ("EC105", "VLSI Design")
    ],
    "EEE": [
        ("EE101", "Circuit Theory"),
        ("EE102", "Power Systems"),
        ("EE103", "Electrical Machines"),
        ("EE104", "Control Systems"),
        ("EE105", "Power Electronics")
    ],
    "Mech": [
        ("ME101", "Thermodynamics"),
        ("ME102", "Fluid Mechanics"),
        ("ME103", "Strength of Materials"),
        ("ME104", "Kinematics of Machinery"),
        ("ME105", "Heat Transfer")
    ],
    "Civil": [
        ("CE101", "Structural Analysis"),
        ("CE102", "Geotechnical Engg"),
        ("CE103", "Fluid Dynamics"),
        ("CE104", "Surveying"),
        ("CE105", "Transportation Engg")
    ]
}

# 8 Engineered test cases: 5 At-Risk, 3 Stars
ENGINEERED_STUDENTS = [
    # 5 At-Risk Cases
    {
        "student_id": "21CSE089",
        "name": "Aarav Sharma",
        "department": "CSE",
        "year": 4,
        "mentor_id": "FAC_CSE_01",
        "ability": 0.28,
        "motivation": 0.25,
        "placement_aptitude": 0.22,
        "cgpa": 5.12,
        "backlogs": 3,
        "attendance_pct": 52.0,
        "lms_logins_avg": 3.0,
        "assignment_completion_pct": 45.0,
        "events": 1,
        "clubs": 0,
        "hackathons": 0,
        "certifications": 0,
        "aptitude": 38.0,
        "coding": 24.0,
        "mock_interviews": 0,
        "technical_score": 35.0,
        "softskill_score": 42.0,
        "satisfaction": 2.1,
        "faculty_rating": 2.4
    },
    {
        "student_id": "22ECE045",
        "name": "Pooja Patel",
        "department": "ECE",
        "year": 3,
        "mentor_id": "FAC_ECE_01",
        "ability": 0.35,
        "motivation": 0.30,
        "placement_aptitude": 0.25,
        "cgpa": 5.38,
        "backlogs": 2,
        "attendance_pct": 58.0,
        "lms_logins_avg": 4.0,
        "assignment_completion_pct": 50.0,
        "events": 2,
        "clubs": 1,
        "hackathons": 0,
        "certifications": 0,
        "aptitude": 42.0,
        "coding": 28.0,
        "mock_interviews": 0,
        "technical_score": 38.0,
        "softskill_score": 46.0,
        "satisfaction": 2.3,
        "faculty_rating": 2.5
    },
    {
        "student_id": "21MECH012",
        "name": "Rahul Verma",
        "department": "Mech",
        "year": 4,
        "mentor_id": "FAC_MECH_01",
        "ability": 0.38,
        "motivation": 0.32,
        "placement_aptitude": 0.28,
        "cgpa": 5.75,
        "backlogs": 4,
        "attendance_pct": 64.0,
        "lms_logins_avg": 5.0,
        "assignment_completion_pct": 52.0,
        "events": 1,
        "clubs": 0,
        "hackathons": 0,
        "certifications": 1,
        "aptitude": 44.0,
        "coding": 18.0,
        "mock_interviews": 0,
        "technical_score": 44.0,
        "softskill_score": 40.0,
        "satisfaction": 2.4,
        "faculty_rating": 2.6
    },
    {
        "student_id": "23CIVIL034",
        "name": "Sneha Kulkarni",
        "department": "Civil",
        "year": 2,
        "mentor_id": "FAC_CIVIL_01",
        "ability": 0.25,
        "motivation": 0.22,
        "placement_aptitude": 0.20,
        "cgpa": 4.90,
        "backlogs": 3,
        "attendance_pct": 49.0,
        "lms_logins_avg": 2.5,
        "assignment_completion_pct": 36.0,
        "events": 0,
        "clubs": 0,
        "hackathons": 0,
        "certifications": 0,
        "aptitude": 35.0,
        "coding": 20.0,
        "mock_interviews": 0,
        "technical_score": 32.0,
        "softskill_score": 38.0,
        "satisfaction": 2.0,
        "faculty_rating": 2.2
    },
    {
        "student_id": "22EEE071",
        "name": "Vikram Singh",
        "department": "EEE",
        "year": 3,
        "mentor_id": "FAC_EEE_01",
        "ability": 0.42,
        "motivation": 0.35,
        "placement_aptitude": 0.30,
        "cgpa": 6.10,
        "backlogs": 2,
        "attendance_pct": 68.0,
        "lms_logins_avg": 5.5,
        "assignment_completion_pct": 58.0,
        "events": 2,
        "clubs": 1,
        "hackathons": 0,
        "certifications": 1,
        "aptitude": 48.0,
        "coding": 31.0,
        "mock_interviews": 0,
        "technical_score": 45.0,
        "softskill_score": 44.0,
        "satisfaction": 2.5,
        "faculty_rating": 2.7
    },
    # 3 Star Students
    {
        "student_id": "21CSE001",
        "name": "Aditi Rao",
        "department": "CSE",
        "year": 4,
        "mentor_id": "FAC_CSE_02",
        "ability": 0.95,
        "motivation": 0.96,
        "placement_aptitude": 0.94,
        "cgpa": 9.65,
        "backlogs": 0,
        "attendance_pct": 96.0,
        "lms_logins_avg": 22.0,
        "assignment_completion_pct": 98.0,
        "events": 14,
        "clubs": 4,
        "hackathons": 5,
        "certifications": 4,
        "aptitude": 92.0,
        "coding": 94.0,
        "mock_interviews": 4,
        "technical_score": 95.0,
        "softskill_score": 90.0,
        "satisfaction": 4.8,
        "faculty_rating": 4.9
    },
    {
        "student_id": "22ECE005",
        "name": "Rohan Iyer",
        "department": "ECE",
        "year": 3,
        "mentor_id": "FAC_ECE_02",
        "ability": 0.92,
        "motivation": 0.93,
        "placement_aptitude": 0.90,
        "cgpa": 9.35,
        "backlogs": 0,
        "attendance_pct": 94.0,
        "lms_logins_avg": 19.5,
        "assignment_completion_pct": 96.0,
        "events": 11,
        "clubs": 3,
        "hackathons": 3,
        "certifications": 3,
        "aptitude": 91.0,
        "coding": 89.0,
        "mock_interviews": 3,
        "technical_score": 92.0,
        "softskill_score": 88.0,
        "satisfaction": 4.7,
        "faculty_rating": 4.8
    },
    {
        "student_id": "21MECH003",
        "name": "Ananya Deshmukh",
        "department": "Mech",
        "year": 4,
        "mentor_id": "FAC_MECH_02",
        "ability": 0.90,
        "motivation": 0.91,
        "placement_aptitude": 0.88,
        "cgpa": 9.15,
        "backlogs": 0,
        "attendance_pct": 93.0,
        "lms_logins_avg": 18.0,
        "assignment_completion_pct": 95.0,
        "events": 9,
        "clubs": 3,
        "hackathons": 2,
        "certifications": 3,
        "aptitude": 88.0,
        "coding": 82.0,
        "mock_interviews": 3,
        "technical_score": 89.0,
        "softskill_score": 86.0,
        "satisfaction": 4.6,
        "faculty_rating": 4.7
    }
]

def generate_base_students():
    """Generate ~600 students with hidden latent traits and realistic correlations."""
    students = []
    eng_ids = {s["student_id"] for s in ENGINEERED_STUDENTS}
    
    # Add engineered students first
    for s in ENGINEERED_STUDENTS:
        students.append(dict(s))
        
    remaining = NUM_STUDENTS - len(ENGINEERED_STUDENTS)
    seq = 10
    
    for i in range(remaining):
        year = random.choice(YEARS)
        dept = random.choice(DEPTS)
        roll_prefix = {1: "24", 2: "23", 3: "22", 4: "21"}[year]
        std_id = f"{roll_prefix}{dept.upper()}{seq:03d}"
        seq += 1
        
        while std_id in eng_ids:
            std_id = f"{roll_prefix}{dept.upper()}{seq:03d}"
            seq += 1
            
        first = random.choice(FIRST_NAMES)
        last = random.choice(LAST_NAMES)
        name = f"{first} {last}"
        mentor_idx = (i % 3) + 1
        mentor_id = f"FAC_{dept.upper()}_{mentor_idx:02d}"
        
        # Latent variables: beta distributions for realistic bell curves
        ability = np.clip(np.random.beta(5, 3), 0.1, 0.98)
        motivation = np.clip(0.6 * ability + 0.4 * np.random.beta(4, 4), 0.1, 0.98)
        placement_aptitude = np.clip(0.5 * ability + 0.5 * np.random.beta(4, 4), 0.1, 0.98)
        
        # Derived metrics with noise
        cgpa = np.clip(4.0 + 5.8 * ability + np.random.normal(0, 0.25), 4.0, 9.95)
        cgpa = round(float(cgpa), 2)
        
        # Backlogs inversely related to ability and motivation
        if ability < 0.35:
            backlogs = int(np.random.choice([2, 3, 4], p=[0.4, 0.4, 0.2]))
        elif ability < 0.50:
            backlogs = int(np.random.choice([0, 1, 2], p=[0.5, 0.35, 0.15]))
        elif ability < 0.70:
            backlogs = int(np.random.choice([0, 1], p=[0.85, 0.15]))
        else:
            backlogs = 0
            
        attendance = np.clip(45.0 + 52.0 * motivation + np.random.normal(0, 4.0), 40.0, 99.0)
        attendance = round(float(attendance), 1)
        
        lms_logins = np.clip(3.0 + 18.0 * motivation + np.random.normal(0, 2.0), 1.0, 30.0)
        lms_logins = round(float(lms_logins), 1)
        
        assign_pct = np.clip(40.0 + 58.0 * motivation + np.random.normal(0, 3.5), 30.0, 100.0)
        assign_pct = round(float(assign_pct), 1)
        
        events = int(np.clip(np.random.poisson(lam=4.0 * motivation), 0, 20))
        clubs = int(np.clip(np.random.poisson(lam=2.0 * motivation), 0, 6))
        hackathons = int(np.clip(np.random.poisson(lam=2.5 * ability * motivation), 0, 8))
        certifications = int(np.clip(np.random.poisson(lam=2.0 * motivation), 0, 6))
        
        aptitude = np.clip(35.0 + 62.0 * placement_aptitude + np.random.normal(0, 3.0), 25.0, 98.0)
        aptitude = round(float(aptitude), 1)
        
        coding = np.clip(30.0 + 67.0 * (0.6 * ability + 0.4 * placement_aptitude) + np.random.normal(0, 4.0), 20.0, 99.0)
        coding = round(float(coding), 1)
        
        if year >= 3:
            mock_interviews = int(np.clip(np.random.poisson(lam=3.0 * placement_aptitude), 0, 5))
        else:
            mock_interviews = int(np.clip(np.random.poisson(lam=0.8 * placement_aptitude), 0, 2))
            
        technical = np.clip(35.0 + 60.0 * ability + np.random.normal(0, 3.0), 25.0, 98.0)
        technical = round(float(technical), 1)
        
        softskill = np.clip(40.0 + 55.0 * (0.5 * motivation + 0.5 * placement_aptitude) + np.random.normal(0, 3.5), 30.0, 96.0)
        softskill = round(float(softskill), 1)
        
        satisfaction = round(float(np.clip(2.0 + 2.8 * motivation + np.random.normal(0, 0.25), 1.0, 5.0)), 1)
        faculty_rating = round(float(np.clip(2.0 + 2.8 * ability + np.random.normal(0, 0.2), 1.0, 5.0)), 1)
        
        student = {
            "student_id": std_id,
            "name": name,
            "department": dept,
            "year": year,
            "mentor_id": mentor_id,
            "ability": round(float(ability), 3),
            "motivation": round(float(motivation), 3),
            "placement_aptitude": round(float(placement_aptitude), 3),
            "cgpa": cgpa,
            "backlogs": backlogs,
            "attendance_pct": attendance,
            "lms_logins_avg": lms_logins,
            "assignment_completion_pct": assign_pct,
            "events": events,
            "clubs": clubs,
            "hackathons": hackathons,
            "certifications": certifications,
            "aptitude": aptitude,
            "coding": coding,
            "mock_interviews": mock_interviews,
            "technical_score": technical,
            "softskill_score": softskill,
            "satisfaction": satisfaction,
            "faculty_rating": faculty_rating
        }
        students.append(student)
        
    return students

def inject_mess_to_df(df, is_id_col="student_id", is_dept_col="department"):
    """
    Inject deliberate mess:
    - Inconsistent IDs (22cse014, CSE-22-014)
    - Department variants (Electronics, E.C.E, C.S.E, Mechanical, Electrical)
    - 5-10% missing values
    - ~3% duplicate rows
    - Out-of-range values (CGPA 11.2, negative marks, attendance 0-1)
    """
    df = df.copy()
    n_rows = len(df)
    eng_ids = {s["student_id"] for s in ENGINEERED_STUDENTS}
    
    # 1. Inconsistent student IDs on ~12% non-engineered rows
    if is_id_col in df.columns:
        for idx in df.index:
            sid = str(df.loc[idx, is_id_col])
            if sid not in eng_ids and random.random() < 0.12:
                # Format: 22CSE014 -> 22cse014 or CSE-22-014
                if len(sid) >= 8:
                    yr = sid[:2]
                    dep = sid[2:-3]
                    num = sid[-3:]
                    if random.random() < 0.5:
                        df.loc[idx, is_id_col] = f"{yr}{dep.lower()}{num}"
                    else:
                        df.loc[idx, is_id_col] = f"{dep.upper()}-{yr}-{num}"

    # 2. Department variants on ~15% non-engineered rows
    if is_dept_col in df.columns:
        dept_aliases = {
            "ECE": ["E.C.E", "Electronics"],
            "CSE": ["C.S.E", "Computer Science"],
            "EEE": ["E.E.E", "Electrical"],
            "Mech": ["Mechanical", "MECH"],
            "Civil": ["CIVIL", "C.I.V.I.L"]
        }
        for idx in df.index:
            if is_id_col in df.columns and df.loc[idx, is_id_col] in eng_ids:
                continue
            cur_dep = str(df.loc[idx, is_dept_col])
            if cur_dep in dept_aliases and random.random() < 0.15:
                df.loc[idx, is_dept_col] = random.choice(dept_aliases[cur_dep])

    # 3. Out-of-range anomalies on ~3% of numeric fields
    for col in df.columns:
        if col in ["student_id", "name", "department", "mentor_id", "ability", "motivation", "placement_aptitude"]:
            continue
        for idx in df.index:
            if is_id_col in df.columns and df.loc[idx, is_id_col] in eng_ids:
                continue
            if random.random() < 0.015:
                if col == "cgpa":
                    df.loc[idx, col] = 11.2 if random.random() < 0.5 else -1.5
                elif col == "attendance_pct":
                    # Attendance as 0-1 scale or over 100
                    if random.random() < 0.6:
                        df.loc[idx, col] = round(float(df.loc[idx, col]) / 100.0, 3)
                    else:
                        df.loc[idx, col] = 108.5
                elif col in ["aptitude", "coding", "technical_score", "marks"]:
                    df.loc[idx, col] = -10.0 if random.random() < 0.5 else 125.0

    # 4. Inject 5-8% missing values in non-key columns
    for col in df.columns:
        if col in ["student_id", "name"]:
            continue
        for idx in df.index:
            if is_id_col in df.columns and df.loc[idx, is_id_col] in eng_ids:
                continue
            if random.random() < 0.06:
                df.loc[idx, col] = np.nan

    # 5. Inject ~3% duplicate rows
    n_dupes = max(1, int(n_rows * 0.03))
    dupe_indices = random.sample(list(df.index), n_dupes)
    dupe_rows = df.loc[dupe_indices].copy()
    df = pd.concat([df, dupe_rows], ignore_index=True)
    
    return df

def seed_all():
    """Generate all 7 raw CSV files and 4 history CSV files."""
    print("Generating base student records (~600 students)...")
    students = generate_base_students()
    df_base = pd.DataFrame(students)
    
    # 1. academic.csv
    academic_cols = ["student_id", "name", "department", "year", "mentor_id", "cgpa", "backlogs"]
    df_academic = inject_mess_to_df(df_base[academic_cols], "student_id", "department")
    df_academic.to_csv(RAW_DIR / "academic.csv", index=False)
    print(f"Generated academic.csv: {len(df_academic)} rows")
    
    # 2. attendance.csv
    attendance_cols = ["student_id", "attendance_pct"]
    df_attendance = inject_mess_to_df(df_base[attendance_cols], "student_id")
    df_attendance.to_csv(RAW_DIR / "attendance.csv", index=False)
    print(f"Generated attendance.csv: {len(df_attendance)} rows")
    
    # 3. lms.csv
    lms_cols = ["student_id", "lms_logins_avg", "assignment_completion_pct"]
    df_lms = inject_mess_to_df(df_base[lms_cols], "student_id")
    df_lms.to_csv(RAW_DIR / "lms.csv", index=False)
    print(f"Generated lms.csv: {len(df_lms)} rows")
    
    # 4. engagement.csv
    eng_cols = ["student_id", "events", "clubs", "hackathons"]
    df_eng = inject_mess_to_df(df_base[eng_cols], "student_id")
    df_eng.to_csv(RAW_DIR / "engagement.csv", index=False)
    print(f"Generated engagement.csv: {len(df_eng)} rows")
    
    # 5. placement.csv
    placement_cols = ["student_id", "aptitude", "coding", "mock_interviews"]
    df_placement = inject_mess_to_df(df_base[placement_cols], "student_id")
    df_placement.to_csv(RAW_DIR / "placement.csv", index=False)
    print(f"Generated placement.csv: {len(df_placement)} rows")
    
    # 6. skills.csv
    skills_cols = ["student_id", "certifications", "technical_score", "softskill_score"]
    df_skills = inject_mess_to_df(df_base[skills_cols], "student_id")
    df_skills.to_csv(RAW_DIR / "skills.csv", index=False)
    print(f"Generated skills.csv: {len(df_skills)} rows")
    
    # 7. feedback.csv
    feedback_cols = ["student_id", "satisfaction", "faculty_rating"]
    df_feedback = inject_mess_to_df(df_base[feedback_cols], "student_id")
    df_feedback.to_csv(RAW_DIR / "feedback.csv", index=False)
    print(f"Generated feedback.csv: {len(df_feedback)} rows")
    
    # History Time-Series Tables
    print("Generating history time-series data...")
    
    # 8. subject_marks.csv (subject-wise marks & attendance for current semester)
    subj_records = []
    for s in students:
        dept = s["department"]
        subjs = SUBJECTS_BY_DEPT.get(dept, SUBJECTS_BY_DEPT["CSE"])
        sem = s["year"] * 2
        for code, name in subjs:
            subj_mark = float(np.clip(s["cgpa"] * 9.5 + np.random.normal(0, 5.0), 30.0, 99.0))
            subj_att = float(np.clip(s["attendance_pct"] + np.random.normal(0, 4.0), 35.0, 100.0))
            subj_records.append({
                "student_id": s["student_id"],
                "subject_code": code,
                "subject_name": name,
                "marks": round(subj_mark, 1),
                "attendance": round(subj_att, 1),
                "semester": sem
            })
    df_subjs = inject_mess_to_df(pd.DataFrame(subj_records), "student_id")
    df_subjs.to_csv(RAW_DIR / "subject_marks.csv", index=False)
    print(f"Generated subject_marks.csv: {len(df_subjs)} rows")
    
    # 9. attendance_history.csv (monthly attendance over past 4 months)
    att_records = []
    months = ["Month 1", "Month 2", "Month 3", "Month 4"]
    eng_ids = {eng["student_id"] for eng in ENGINEERED_STUDENTS}
    for s in students:
        base_att = s["attendance_pct"]
        sid = s["student_id"]
        is_at_risk = sid in ["21CSE089", "22ECE045", "21MECH012", "23CIVIL034", "22EEE071"]
        is_eng = sid in eng_ids
        is_mech_y2 = (s["department"] == "Mech" and int(s["year"]) == 2 and not is_eng)

        for i, m in enumerate(months):
            if is_at_risk:
                m_att = max(35.0, base_att + (3 - i) * 3.5 + np.random.normal(0, 1.5))
            elif is_mech_y2:
                # Mech Year 2 attendance declining by about 8 points across months 1 to 4 (+4 in M1 to -4 in M4)
                m_att = np.clip(base_att + (1.5 - i) * 2.7 + np.random.normal(0, 1.5), 30.0, 100.0)
            else:
                m_att = np.clip(base_att + np.random.normal(0, 2.5), 40.0, 100.0)
            att_records.append({
                "student_id": s["student_id"],
                "month": m,
                "attendance_pct": round(float(m_att), 1)
            })
    df_att_hist = inject_mess_to_df(pd.DataFrame(att_records), "student_id")
    df_att_hist.to_csv(RAW_DIR / "attendance_history.csv", index=False)
    print(f"Generated attendance_history.csv: {len(df_att_hist)} rows")
    
    # 10. lms_history.csv (weekly LMS logins over past 8 weeks)
    lms_records = []
    for s in students:
        base_logins = s["lms_logins_avg"]
        sid = s["student_id"]
        is_eng = sid in eng_ids
        is_cse_y3 = (s["department"] == "CSE" and int(s["year"]) == 3 and not is_eng)

        for w in range(1, 9):
            if is_cse_y3 and w >= 5:
                # CSE Year 3 LMS logins falling about 25% over weeks 5 to 8
                eff_base = base_logins * 0.75
            else:
                eff_base = base_logins
            logins = max(0, int(round(np.random.normal(eff_base, 1.5))))
            assigns = 1 if (logins > 3 and random.random() < 0.7) else 0
            lms_records.append({
                "student_id": s["student_id"],
                "week": f"Week {w}",
                "logins": logins,
                "assignments_completed": assigns
            })
    df_lms_hist = inject_mess_to_df(pd.DataFrame(lms_records), "student_id")
    df_lms_hist.to_csv(RAW_DIR / "lms_history.csv", index=False)
    print(f"Generated lms_history.csv: {len(df_lms_hist)} rows")
    
    # 11. semester_history.csv (up to 8 semesters of CGPA / SGPA history)
    sem_records = []
    eng_ids = {eng["student_id"] for eng in ENGINEERED_STUDENTS}
    for s in students:
        max_sem = min(8, int(s["year"]) * 2)
        target_cgpa = float(s["cgpa"])
        is_eng = s["student_id"] in eng_ids
        is_at_risk = s["student_id"] in ["21CSE089", "22ECE045", "21MECH012", "23CIVIL034", "22EEE071"]
        
        # Build a smooth trajectory ending exactly at target_cgpa in max_sem
        if max_sem == 1:
            cgpas = [target_cgpa]
        else:
            if is_at_risk:
                start_cgpa = min(9.5, target_cgpa + 1.2)
            elif is_eng:
                start_cgpa = max(5.0, target_cgpa - 0.4)
            else:
                start_cgpa = np.clip(target_cgpa + np.random.uniform(-0.3, 0.3), 4.5, 9.8)
            
            # Linear trend with subtle noise, pinned at start and end
            cgpas = np.linspace(start_cgpa, target_cgpa, max_sem)
            if max_sem > 2:
                noise = np.random.normal(0, 0.05, max_sem)
                noise[0] = 0.0
                noise[-1] = 0.0
                cgpas = np.clip(cgpas + noise, 3.5, 9.9)
            cgpas[-1] = target_cgpa  # Guaranteed exact match at final semester

        for sem in range(1, max_sem + 1):
            curr_c = round(float(cgpas[sem - 1]), 2)
            if sem == 1:
                sgpa = curr_c
            else:
                prev_c = cgpas[sem - 2]
                # sem * curr_c - (sem-1)*prev_c approx sgpa
                sgpa = np.clip(round(float(sem * curr_c - (sem - 1) * prev_c), 2), 2.5, 10.0)
            
            sem_records.append({
                "student_id": s["student_id"],
                "semester": sem,
                "sgpa": sgpa,
                "cgpa": curr_c,
                "backlogs": int(s.get("backlogs", 0)) if sem == max_sem else (1 if (is_at_risk and sem >= 3) else 0)
            })
    df_sem_hist = inject_mess_to_df(pd.DataFrame(sem_records), "student_id")
    df_sem_hist.to_csv(RAW_DIR / "semester_history.csv", index=False)
    print(f"Generated semester_history.csv: {len(df_sem_hist)} rows")
    
    print("\nData seeding complete! All 7 source CSVs + 4 time-series CSVs saved to data/raw/")

if __name__ == "__main__":
    seed_all()
