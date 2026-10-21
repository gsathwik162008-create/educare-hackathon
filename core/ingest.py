"""
Smart Campus Analytics - Data Ingestion & Cleaning Pipeline
Integrates 7 raw CSV sources and 4 time-series tables into SQLite.
Implements modular cleaning rules: ID standardisation, department mapping,
duplicate removal, scale unification, range clipping, and documented imputation.
All transformations are logged to the `cleaning_log` table.
"""

import re
import sqlite3
import pandas as pd
import numpy as np
from datetime import datetime
from pathlib import Path
from core.config import (
    RAW_DATA_DIR,
    DB_PATH,
    DEPARTMENT_MAPPING,
    VALUE_BOUNDS,
    DATA_DIR
)

# In-memory accumulator for cleaning audit log
_cleaning_audit_records = []

def log_cleaning_action(file_name: str, issue_type: str, rows_affected: int,
                        action: str, before_count: int, after_count: int):
    """Record an audit entry for data cleaning actions."""
    if rows_affected > 0:
        _cleaning_audit_records.append({
            "file": file_name,
            "issue_type": issue_type,
            "rows_affected": int(rows_affected),
            "action": action,
            "before_count": int(before_count),
            "after_count": int(after_count),
            "logged_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })

def standardise_student_id(series: pd.Series, file_name: str = "unknown") -> pd.Series:
    """Rule 1: Standardise student roll IDs to consistent format (e.g. 22CSE014)."""
    before_count = len(series)
    fixed_count = 0
    clean_series = series.copy()

    for idx, val in series.items():
        if pd.isna(val):
            continue
        s = str(val).strip().upper()
        # Case A: Format like CSE-22-014 -> 22CSE014
        m_dash = re.match(r"^([A-Z]+)[-_](\d{2})[-_](\d{3})$", s)
        if m_dash:
            dept, yr, num = m_dash.groups()
            new_id = f"{yr}{dept}{num}"
            clean_series.loc[idx] = new_id
            fixed_count += 1
            continue
            
        # Case B: Format like 22cse014 or mixed casing / spaces
        m_std = re.match(r"^(\d{2})([A-Z]+)(\d{3})$", s)
        if m_std:
            clean_series.loc[idx] = s
            if s != str(val):
                fixed_count += 1
        else:
            clean_series.loc[idx] = s

    log_cleaning_action(
        file_name=file_name,
        issue_type="inconsistent_id_format",
        rows_affected=fixed_count,
        action="Standardised student ID syntax to YYDEPTNNN format",
        before_count=before_count,
        after_count=before_count
    )
    return clean_series

def standardise_department(series: pd.Series, file_name: str = "unknown") -> pd.Series:
    """Rule 2: Standardise department names using canonical mapping."""
    before_count = len(series)
    fixed_count = 0
    clean_series = series.copy()

    for idx, val in series.items():
        if pd.isna(val):
            continue
        v_clean = str(val).strip().upper()
        mapped = DEPARTMENT_MAPPING.get(v_clean)
        if mapped and mapped != val:
            clean_series.loc[idx] = mapped
            fixed_count += 1
        elif mapped:
            clean_series.loc[idx] = mapped
        else:
            clean_series.loc[idx] = str(val).strip()

    log_cleaning_action(
        file_name=file_name,
        issue_type="department_variant",
        rows_affected=fixed_count,
        action="Mapped department variants to canonical names",
        before_count=before_count,
        after_count=before_count
    )
    return clean_series

def remove_duplicates(df: pd.DataFrame, subset: list, file_name: str = "unknown") -> pd.DataFrame:
    """Rule 3: Remove duplicate records based on primary identifier subset."""
    before_count = len(df)
    df_clean = df.drop_duplicates(subset=subset, keep="first").copy()
    after_count = len(df_clean)
    dupes_removed = before_count - after_count

    log_cleaning_action(
        file_name=file_name,
        issue_type="duplicate_rows",
        rows_affected=dupes_removed,
        action=f"Removed duplicate rows keyed on {subset}",
        before_count=before_count,
        after_count=after_count
    )
    return df_clean

def unify_scales(df: pd.DataFrame, file_name: str = "unknown") -> pd.DataFrame:
    """Rule 4: Unify percentage metrics represented as decimals (0-1) to 0-100 scale."""
    before_count = len(df)
    df_clean = df.copy()
    total_scaled = 0

    pct_cols = [c for c in df_clean.columns if "pct" in c or c == "attendance"]
    for col in pct_cols:
        if pd.api.types.is_numeric_dtype(df_clean[col]):
            mask = (df_clean[col] > 0.0) & (df_clean[col] <= 1.0)
            rows_affected = mask.sum()
            if rows_affected > 0:
                df_clean.loc[mask, col] = (df_clean.loc[mask, col] * 100.0).round(1)
                total_scaled += rows_affected

    log_cleaning_action(
        file_name=file_name,
        issue_type="scale_mismatch",
        rows_affected=total_scaled,
        action="Multiplied decimal ratios (0-1) by 100 to standardise percentage scale",
        before_count=before_count,
        after_count=before_count
    )
    return df_clean

def clip_out_of_range(df: pd.DataFrame, file_name: str = "unknown") -> pd.DataFrame:
    """Rule 5: Treat out-of-range values as missing (NaN) for subsequent statistical imputation."""
    before_count = len(df)
    df_clean = df.copy()

    for col in df_clean.columns:
        if col in VALUE_BOUNDS and pd.api.types.is_numeric_dtype(df_clean[col]):
            min_val, max_val = VALUE_BOUNDS[col]
            mask = (df_clean[col] < min_val) | (df_clean[col] > max_val)
            rows_affected = int(mask.sum())
            if rows_affected > 0:
                df_clean.loc[mask, col] = np.nan
                log_cleaning_action(
                    file_name=file_name,
                    issue_type="invalid_value_imputed",
                    rows_affected=rows_affected,
                    action=f"Column '{col}': set {rows_affected} invalid out-of-range values to NaN for imputation",
                    before_count=before_count,
                    after_count=before_count
                )

    return df_clean

def impute_missing_values(df: pd.DataFrame, file_name: str = "unknown") -> (pd.DataFrame, pd.Series):
    """
    Rule 6: Impute missing entries with documented statistical fallbacks:
    - Academic/skills scores: department median
    - Counts (backlogs, events, hackathons, certs): 0
    - Returns cleaned df and count of imputed fields per row for confidence tracking.
    """
    before_count = len(df)
    df_clean = df.copy()
    imputed_mask = df_clean.isna()
    imputed_per_row = imputed_mask.sum(axis=1)
    total_missing = imputed_mask.sum().sum()

    count_cols = ["backlogs", "events", "clubs", "hackathons", "certifications", "mock_interviews"]
    for col in count_cols:
        if col in df_clean.columns:
            df_clean[col] = df_clean[col].fillna(0)

    # Department median imputation for continuous variables
    has_dept = "department" in df_clean.columns
    for col in df_clean.columns:
        if col in ["student_id", "name", "mentor_id", "department"]:
            continue
        if pd.api.types.is_numeric_dtype(df_clean[col]) and df_clean[col].isna().any():
            if has_dept:
                dept_medians = df_clean.groupby("department")[col].transform("median")
                df_clean[col] = df_clean[col].fillna(dept_medians)
            global_med = df_clean[col].median()
            df_clean[col] = df_clean[col].fillna(global_med if pd.notna(global_med) else 0)

    # Categorical fallbacks: infer department from student_id roll code or mentor_id
    if "department" in df_clean.columns and df_clean["department"].isna().any():
        dept_missing_mask = df_clean["department"].isna()
        dept_missing_count = int(dept_missing_mask.sum())
        for idx in df_clean[dept_missing_mask].index:
            inferred = None
            if "student_id" in df_clean.columns:
                sid = str(df_clean.loc[idx, "student_id"]).strip().upper()
                m = re.match(r"^\d{2}([A-Z]+)\d{3}$", sid)
                if m:
                    code = m.group(1)
                    inferred = DEPARTMENT_MAPPING.get(code)
            if not inferred and "mentor_id" in df_clean.columns:
                mentor = str(df_clean.loc[idx, "mentor_id"]).upper()
                for d_key, d_val in DEPARTMENT_MAPPING.items():
                    if d_key in mentor:
                        inferred = d_val
                        break
            df_clean.loc[idx, "department"] = inferred if inferred else "CSE"

        log_cleaning_action(
            file_name=file_name,
            issue_type="missing_department_inferred",
            rows_affected=dept_missing_count,
            action=f"Inferred {dept_missing_count} missing departments from student roll number ID syntax",
            before_count=before_count,
            after_count=before_count
        )

    if "mentor_id" in df_clean.columns and df_clean["mentor_id"].isna().any():
        df_clean["mentor_id"] = df_clean["mentor_id"].fillna("FAC_GEN_01")

    log_cleaning_action(
        file_name=file_name,
        issue_type="missing_values",
        rows_affected=total_missing,
        action="Imputed missing values using department medians or zero-defaults",
        before_count=before_count,
        after_count=before_count
    )
    return df_clean, imputed_per_row

def clean_source_dataframe(df: pd.DataFrame, file_name: str, key_subset: list) -> pd.DataFrame:
    """Run all cleaning rules on a single raw dataframe."""
    df_clean = df.copy()
    
    # 1. Standardise ID
    if "student_id" in df_clean.columns:
        df_clean["student_id"] = standardise_student_id(df_clean["student_id"], file_name)
        
    # 2. Standardise Department
    if "department" in df_clean.columns:
        df_clean["department"] = standardise_department(df_clean["department"], file_name)
        
    # 3. Unify percentage scales
    df_clean = unify_scales(df_clean, file_name)
    
    # 4. Clip out of range
    df_clean = clip_out_of_range(df_clean, file_name)
    
    # 5. Remove duplicates
    df_clean = remove_duplicates(df_clean, subset=key_subset, file_name=file_name)
    
    return df_clean

def ingest_all(verbose: bool = True) -> dict:
    """
    Ingest, clean, and merge all 7 sources into `students_unified`,
    plus 4 time-series tables into SQLite `data/campus.db`.
    Supports re-running idempotently without duplicating rows.
    """
    global _cleaning_audit_records
    _cleaning_audit_records = []
    
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    
    if verbose:
        print("Ingesting and cleaning 7 raw data sources...")

    # Load 7 raw sources
    raw_academic = pd.read_csv(RAW_DATA_DIR / "academic.csv")
    raw_attendance = pd.read_csv(RAW_DATA_DIR / "attendance.csv")
    raw_lms = pd.read_csv(RAW_DATA_DIR / "lms.csv")
    raw_engagement = pd.read_csv(RAW_DATA_DIR / "engagement.csv")
    raw_placement = pd.read_csv(RAW_DATA_DIR / "placement.csv")
    raw_skills = pd.read_csv(RAW_DATA_DIR / "skills.csv")
    raw_feedback = pd.read_csv(RAW_DATA_DIR / "feedback.csv")

    # Clean each source
    df_acad = clean_source_dataframe(raw_academic, "academic.csv", ["student_id"])
    df_att = clean_source_dataframe(raw_attendance, "attendance.csv", ["student_id"])
    df_lms = clean_source_dataframe(raw_lms, "lms.csv", ["student_id"])
    df_eng = clean_source_dataframe(raw_engagement, "engagement.csv", ["student_id"])
    df_place = clean_source_dataframe(raw_placement, "placement.csv", ["student_id"])
    df_skills = clean_source_dataframe(raw_skills, "skills.csv", ["student_id"])
    df_feed = clean_source_dataframe(raw_feedback, "feedback.csv", ["student_id"])

    # Merge sequentially into a unified student record
    unified = df_acad.copy()
    sources = [df_att, df_lms, df_eng, df_place, df_skills, df_feed]
    for s in sources:
        unified = pd.merge(unified, s, on="student_id", how="left")

    # Impute missing values on unified dataframe
    unified, imputed_counts = impute_missing_values(unified, "students_unified")
    unified["imputed_field_count"] = imputed_counts

    # Ensure required columns order
    expected_cols = [
        "student_id", "name", "department", "year", "mentor_id", "cgpa",
        "backlogs", "attendance_pct", "lms_logins_avg", "assignment_completion_pct",
        "events", "clubs", "hackathons", "certifications", "aptitude", "coding",
        "mock_interviews", "technical_score", "softskill_score", "satisfaction",
        "faculty_rating", "imputed_field_count"
    ]
    unified = unified[[c for c in expected_cols if c in unified.columns]]
    
    # Save unified to SQLite (replaces table cleanly)
    unified.to_sql("students_unified", conn, if_exists="replace", index=False)
    if verbose:
        print(f"Table 'students_unified' written: {len(unified)} records")

    # Ingest and clean 4 time-series history tables
    # 1. subject_marks
    raw_subjs = pd.read_csv(RAW_DATA_DIR / "subject_marks.csv")
    df_subjs = clean_source_dataframe(raw_subjs, "subject_marks.csv", ["student_id", "subject_code"])
    df_subjs, _ = impute_missing_values(df_subjs, "subject_marks.csv")
    df_subjs.to_sql("subject_marks", conn, if_exists="replace", index=False)
    
    # 2. attendance_history
    raw_att_hist = pd.read_csv(RAW_DATA_DIR / "attendance_history.csv")
    
    # Infer missing month where a student has missing month(s) from 1-4
    raw_att_hist["student_id"] = standardise_student_id(raw_att_hist["student_id"], "attendance_history.csv")
    all_months = ["Month 1", "Month 2", "Month 3", "Month 4"]
    inferred_month_count = 0
    
    for sid, group in raw_att_hist.groupby("student_id"):
        null_indices = group[group["month"].isna()].index
        if len(null_indices) > 0:
            present = set(group["month"].dropna())
            missing = [m for m in all_months if m not in present]
            for i, null_idx in enumerate(null_indices):
                if i < len(missing):
                    raw_att_hist.loc[null_idx, "month"] = missing[i]
                    inferred_month_count += 1
    
    log_cleaning_action("attendance_history.csv", "missing_key_inferred", inferred_month_count,
                        "Inferred missing month values from 1-4 sequence for students with blank months",
                        len(raw_att_hist), len(raw_att_hist))

    df_att_hist = clean_source_dataframe(raw_att_hist, "attendance_history.csv", ["student_id", "month"])
    df_att_hist, _ = impute_missing_values(df_att_hist, "attendance_history.csv")
    df_att_hist.to_sql("attendance_history", conn, if_exists="replace", index=False)

    # 3. lms_history
    raw_lms_hist = pd.read_csv(RAW_DATA_DIR / "lms_history.csv")
    df_lms_hist = clean_source_dataframe(raw_lms_hist, "lms_history.csv", ["student_id", "week"])
    df_lms_hist, _ = impute_missing_values(df_lms_hist, "lms_history.csv")
    df_lms_hist.to_sql("lms_history", conn, if_exists="replace", index=False)

    # 4. semester_history
    raw_sem_hist = pd.read_csv(RAW_DATA_DIR / "semester_history.csv")
    df_sem_hist = clean_source_dataframe(raw_sem_hist, "semester_history.csv", ["student_id", "semester"])
    df_sem_hist, _ = impute_missing_values(df_sem_hist, "semester_history.csv")

    # Reconcile longitudinal semester_history so final cumulative CGPA equals stated current CGPA in students_unified
    # Anchor: students_unified.cgpa is the single source of truth for current standing.
    u_cgpa_map = dict(zip(unified["student_id"], unified["cgpa"]))
    sem_reconciled_count = 0
    df_sem_hist = df_sem_hist.sort_values(by=["student_id", "semester"]).reset_index(drop=True)
    last_sem_indices = df_sem_hist.groupby("student_id")["semester"].idxmax()
    for sid, idx in last_sem_indices.items():
        if sid in u_cgpa_map:
            target_cgpa = float(u_cgpa_map[sid])
            if abs(df_sem_hist.loc[idx, "cgpa"] - target_cgpa) > 0.00001:
                df_sem_hist.loc[idx, "cgpa"] = target_cgpa
                sem_reconciled_count += 1

    log_cleaning_action("semester_history.csv", "CGPA Reconciliation with students_unified", sem_reconciled_count,
                        "Synchronized final cumulative CGPA to match students_unified.cgpa exactly", len(df_sem_hist), len(df_sem_hist))

    df_sem_hist.to_sql("semester_history", conn, if_exists="replace", index=False)

    # Save cleaning audit log to SQLite
    df_log = pd.DataFrame(_cleaning_audit_records)
    df_log.to_sql("cleaning_log", conn, if_exists="replace", index=False)
    if verbose:
        print(f"Table 'cleaning_log' written: {len(df_log)} audit entries (reconciled {sem_reconciled_count} student history records)")

    conn.close()
    
    stats = {
        "unified_students": len(unified),
        "audit_log_entries": len(df_log),
        "total_fixes": df_log["rows_affected"].sum() if not df_log.empty else 0
    }
    return stats

if __name__ == "__main__":
    results = ingest_all(verbose=True)
    print("\nIngestion pipeline successfully completed:")
    print(results)
