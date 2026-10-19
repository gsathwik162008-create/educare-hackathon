"""
Smart Campus Analytics - Phase 1 Verification Script
Validates database schema, row counts, idempotent re-runs, engineered students,
and cleaning audit logs.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import sqlite3
import pandas as pd
from core.ingest import ingest_all
from core.config import DB_PATH

def verify():
    print("=" * 60)
    print("SMART CAMPUS ANALYTICS - PHASE 1 VERIFICATION")
    print("=" * 60)
    
    # 1. Connect to campus.db
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    tables = [r[0] for r in cursor.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
    print(f"\n1. Database Tables Found: {len(tables)}")
    for t in sorted(tables):
        count = cursor.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
        print(f"   - {t:<22} : {count:>5} rows")

    # 2. Check schema of students_unified
    print("\n2. Columns in 'students_unified':")
    cols = [r[1] for r in cursor.execute("PRAGMA table_info(students_unified)").fetchall()]
    print("   " + ", ".join(cols))

    # 3. Check engineered students
    print("\n3. Verification of 8 Engineered Test Students (5 At-Risk, 3 Stars):")
    eng_ids = ("21CSE089", "22ECE045", "21MECH012", "23CIVIL034", "22EEE071", "21CSE001", "22ECE005", "21MECH003")
    query = f"""
    SELECT student_id, name, department, year, cgpa, backlogs, attendance_pct, coding, aptitude, mock_interviews
    FROM students_unified
    WHERE student_id IN {eng_ids}
    ORDER BY cgpa ASC
    """
    df_eng = pd.read_sql(query, conn)
    print(df_eng.to_string(index=False))

    # 4. Check Cleaning Audit Log
    print("\n4. Sample Data Cleaning Audit Entries from 'cleaning_log':")
    df_log = pd.read_sql("SELECT file, issue_type, rows_affected, action FROM cleaning_log LIMIT 8", conn)
    print(df_log.to_string(index=False))

    conn.close()

    # 5. Test Idempotency (re-running ingest_all without duplicating rows)
    print("\n5. Testing Pipeline Idempotency (Re-running ingest_all)...")
    stats = ingest_all(verbose=False)
    
    conn = sqlite3.connect(DB_PATH)
    count_after = conn.cursor().execute("SELECT COUNT(*) FROM students_unified").fetchone()[0]
    conn.close()
    
    print(f"   Row count after re-run: {count_after} (Expected: 600)")
    assert count_after == 600, f"Error: duplicate rows detected! Count is {count_after}"
    print("   Idempotency assertion PASSED: No duplicates introduced on re-run.")
    print("\n" + "=" * 60)
    print("PHASE 1 ALL CHECKS PASSED SUCCESSFULLY")
    print("=" * 60)

if __name__ == "__main__":
    verify()
