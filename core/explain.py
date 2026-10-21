"""
Smart Campus Analytics - Explanation Engine
Generates plain-English narrative explanations for faculty and supportive
growth-oriented guidance for student portals using deterministic sentence templates.
Supports optional LLM-enhanced narratives loaded strictly from cached JSON.
"""

import json
import pandas as pd
from pathlib import Path
from core.config import LLM_CACHE_PATH
from core.interventions import get_student_specific_interventions

# In-memory cached LLM explanations
_llm_cache = None

def load_llm_cache():
    """Load cached qualitative explanations from JSON storage."""
    global _llm_cache
    if _llm_cache is None:
        if LLM_CACHE_PATH.exists():
            try:
                with open(LLM_CACHE_PATH, "r", encoding="utf-8") as f:
                    _llm_cache = json.load(f)
            except Exception:
                _llm_cache = {}
        else:
            _llm_cache = {}
    return _llm_cache

def explain_for_faculty(student_dict):
    """
    Generate an analyst-grade narrative explanation for faculty and administrators.
    Highlights scores, sub-scores, top drags, strengths, multi-factor risk flags,
    and prioritized intervention actions directly from the intervention engine.
    """
    score = student_dict.get("success_score", 0.0)
    acad = student_dict.get("academic_health", 0.0)
    place = student_dict.get("placement_readiness", 0.0)
    drags = student_dict.get("top_drags", "None")
    strengths = student_dict.get("top_strengths", "None")
    reasons = student_dict.get("risk_reasons", "Normal academic & placement standing")

    # Read prioritized action directly from intervention engine (Single Source of Truth)
    action_priority, pot_gain, primary_action, selected_gaps = get_student_specific_interventions(student_dict)

    text = (
        f"Success score {score:.1f} ({acad:.1f} academic health, {place:.1f} placement readiness). "
        f"Biggest drags: {drags}. "
        f"Key strengths: {strengths}. "
        f"Risk profile: {reasons}. "
        f"Recommended intervention: {primary_action} (action priority {action_priority:.2f}, estimated potential gain +{pot_gain:.1f} pts)."
    )
    return text

def explain_for_student(student_dict):
    """
    Generate an encouraging, growth-oriented explanation for the student portal.
    RULE: Never uses words 'risk', 'at-risk', student rank, or segment names.
    Uses positive language ('biggest opportunity: coding score').
    """
    score = student_dict.get("success_score", 0.0)
    strengths = student_dict.get("top_strengths", "")
    
    # Clean strengths for student view (remove raw negative/positive math notation)
    clean_strengths = strengths.replace("(+", "(").replace(" pts)", " impact)") if strengths != "None" else "consistent coursework"
    
    # Read prioritized action directly from intervention engine
    action_priority, pot_gain, primary_action, selected_gaps = get_student_specific_interventions(student_dict)
    
    if selected_gaps:
        opp_list = [f"{g['target_metric'].replace('_pct', '').replace('_', ' ')}" for g in selected_gaps]
        opportunities = " and ".join(opp_list)
    else:
        opportunities = "advanced specialization and project leadership"

    text = (
        f"Your current success score is {score:.1f}. "
        f"Your strongest foundational areas include: {clean_strengths}. "
        f"Your biggest opportunity for growth is: {opportunities}. "
        f"Recommended next step: {primary_action}. "
        f"Completing this focus area can improve your progress by an estimated +{pot_gain:.1f} points."
    )
    return text

def compute_semesters_remaining(student_dict: dict) -> int:
    """
    Compute semesters remaining from year and semester:
    Total program is 8 semesters (4 years * 2 semesters/year).
    Current semester = student.get('semester') or (year * 2).
    Remaining semesters = max(0, 8 - current_semester).
    """
    total_semesters = 8
    year = int(float(student_dict.get("year", 4)))
    sem = student_dict.get("semester")
    if sem is not None and not pd.isna(sem):
        current_sem = int(float(sem))
    else:
        current_sem = min(8, year * 2)
    return max(0, total_semesters - current_sem)

def validate_narrative_numbers(narrative: str, student_dict: dict) -> bool:
    """
    Validator that checks numbers mentioned in a cached narrative against the DB record.
    Extracts floating-point and integer numbers from text and checks whether each matches
    at least one known attribute of the student (or standard constant).
    Falls back to template text if any factual metric mismatches.
    """
    if not narrative:
        return False

    import re

    # Number word map
    word_to_num = {
        "zero": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
        "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10
    }

    # 1. Compile valid set of student metrics
    valid_nums = set()
    for k, v in student_dict.items():
        if isinstance(v, (int, float)) and not pd.isna(v):
            valid_nums.add(round(float(v), 1))
            valid_nums.add(round(float(v), 2))
            valid_nums.add(int(round(float(v))))
    
    # Include current semester and semesters remaining
    sem_rem = compute_semesters_remaining(student_dict)
    valid_nums.update({
        sem_rem,
        0, 4, 8, 10, 50, 70, 75, 100
    })

    # Action specific potential gains if available
    try:
        from core.interventions import get_student_specific_interventions
        _, pot_gain, _, _ = get_student_specific_interventions(student_dict)
        valid_nums.add(round(float(pot_gain), 1))
    except Exception:
        pass

    # 2. Check numbers written as words (e.g. "two semesters", "three backlogs")
    word_tokens = re.findall(r"\b(zero|one|two|three|four|five|six|seven|eight|nine|ten)\b", narrative, re.IGNORECASE)
    for wt in word_tokens:
        w_val = word_to_num[wt.lower()]
        # If phrase is specifically about semesters remaining, check against sem_rem
        if re.search(rf"\b{wt}\s+semesters?\s+remaining\b", narrative, re.IGNORECASE):
            if w_val != sem_rem:
                return False
        # General check: number must be valid student attribute
        if w_val not in valid_nums:
            return False

    # 3. Check digit tokens
    tokens = re.findall(r"(?<![a-zA-Z_])\b\d+(?:\.\d+)?\b(?![a-zA-Z_])", narrative)
    for tok in tokens:
        try:
            val = float(tok)
            if round(val, 1) not in valid_nums and int(round(val)) not in valid_nums:
                return False
        except ValueError:
            continue

    return True

def get_enhanced_explanation(student_id: str, role: str = "faculty", student_dict: dict = None) -> str:
    """
    Returns an explanation for the specified student and role.
    Validates numbers in cached LLM text against the database;
    falls back to the template text if any number mismatches or text is missing.
    """
    sid = str(student_id).strip().upper()
    role_key = role.lower()

    if student_dict is None:
        import sqlite3
        from core.config import DB_PATH
        conn = sqlite3.connect(DB_PATH)
        row = conn.cursor().execute("SELECT * FROM students_scored WHERE student_id = ?", (sid,)).fetchone()
        if row:
            cols = [d[0] for d in conn.cursor().execute("PRAGMA table_info(students_scored)").fetchall()]
            student_dict = dict(zip(cols, row))
        else:
            student_dict = {}
        conn.close()

    template_text = explain_for_student(student_dict) if role_key == "student" else explain_for_faculty(student_dict)

    cache = load_llm_cache()
    if sid in cache and role_key in cache[sid]:
        cached_text = cache[sid][role_key]
        if validate_narrative_numbers(cached_text, student_dict):
            return cached_text
        else:
            # Fall back to template text if numbers mismatch
            return template_text

    return template_text
