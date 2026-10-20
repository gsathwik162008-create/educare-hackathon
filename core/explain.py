"""
Smart Campus Analytics - Explanation Engine
Generates plain-English narrative explanations for faculty and supportive
growth-oriented guidance for student portals using deterministic sentence templates.
Supports optional LLM-enhanced narratives loaded strictly from cached JSON.
"""

import json
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

def get_enhanced_explanation(student_id: str, role: str = "faculty", student_dict: dict = None) -> str:
    """
    Returns an explanation for the specified student and role.
    Checks the local cached LLM JSON store first; if not found, falls back
    to deterministic sentence templates.
    """
    cache = load_llm_cache()
    sid = str(student_id).strip().upper()
    role_key = role.lower()

    if sid in cache and role_key in cache[sid]:
        return cache[sid][role_key]

    # Deterministic fallback using templates
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

    if role_key == "student":
        return explain_for_student(student_dict)
    else:
        return explain_for_faculty(student_dict)
