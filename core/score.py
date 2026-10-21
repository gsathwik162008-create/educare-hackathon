"""
Smart Campus Analytics - Student Scoring and Risk Engine
Computes Success Scores (0-100), Academic Health, Placement Readiness,
Indicator Drivers (top drags and strengths), Multi-factor Risk Flags,
Longitudinal Trend Deltas, Rule-based and K-Means Segments, and Data Confidence.
All calculations output to the `students_scored` table in SQLite.
"""

import sqlite3
import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler

from core.config import (
    DB_PATH,
    WEIGHTS,
    THRESHOLDS,
    SEGMENTS,
    DRIVER_INDICATORS
)

def normalize_metrics(df_or_dict):
    """
    Normalise all student performance metrics to a standard [0, 100] scale.
    Works on both pandas DataFrame and dictionary (for what-if simulator).
    """
    is_df = isinstance(df_or_dict, pd.DataFrame)
    data = df_or_dict.copy() if is_df else dict(df_or_dict)

    def get_val(key, default=0.0):
        if is_df:
            return data[key] if key in data.columns else pd.Series(default, index=data.index)
        return data.get(key, default)

    cgpa = get_val("cgpa", 0.0)
    backlogs = get_val("backlogs", 0.0)
    attendance = get_val("attendance_pct", 0.0)
    coding = get_val("coding", 0.0)
    aptitude = get_val("aptitude", 0.0)
    mock_interviews = get_val("mock_interviews", 0.0)
    lms_logins = get_val("lms_logins_avg", 0.0)
    assignment_pct = get_val("assignment_completion_pct", 0.0)
    events = get_val("events", 0.0)
    clubs = get_val("clubs", 0.0)
    hackathons = get_val("hackathons", 0.0)
    certifications = get_val("certifications", 0.0)
    technical = get_val("technical_score", 0.0)
    softskill = get_val("softskill_score", 0.0)
    satisfaction = get_val("satisfaction", 3.0)
    faculty_rating = get_val("faculty_rating", 3.0)

    if is_df:
        norm = pd.DataFrame(index=data.index)
        norm["cgpa_norm"] = (cgpa * 10.0).clip(0.0, 100.0)
        norm["backlogs_norm"] = (100.0 - (backlogs * 20.0)).clip(0.0, 100.0)
        norm["attendance_pct"] = attendance.clip(0.0, 100.0)
        norm["coding"] = coding.clip(0.0, 100.0)
        norm["aptitude"] = aptitude.clip(0.0, 100.0)
        norm["mock_interviews_norm"] = (mock_interviews * 25.0).clip(0.0, 100.0)
        norm["lms_logins_norm"] = ((lms_logins / 25.0) * 100.0).clip(0.0, 100.0)
        norm["assignment_completion_pct"] = assignment_pct.clip(0.0, 100.0)
        norm["engagement_score"] = (events * 4.0 + clubs * 10.0 + hackathons * 15.0).clip(0.0, 100.0)
        norm["certifications_norm"] = (certifications * 25.0).clip(0.0, 100.0)
        norm["technical_score"] = technical.clip(0.0, 100.0)
        norm["softskill_score"] = softskill.clip(0.0, 100.0)
        norm["feedback_norm"] = (((faculty_rating - 1.0) / 4.0) * 50.0 + ((satisfaction - 1.0) / 4.0) * 50.0).clip(0.0, 100.0)
        return norm
    else:
        norm = {
            "cgpa_norm": float(np.clip(cgpa * 10.0, 0.0, 100.0)),
            "backlogs_norm": float(np.clip(100.0 - (backlogs * 20.0), 0.0, 100.0)),
            "attendance_pct": float(np.clip(attendance, 0.0, 100.0)),
            "coding": float(np.clip(coding, 0.0, 100.0)),
            "aptitude": float(np.clip(aptitude, 0.0, 100.0)),
            "mock_interviews_norm": float(np.clip(mock_interviews * 25.0, 0.0, 100.0)),
            "lms_logins_norm": float(np.clip((lms_logins / 25.0) * 100.0, 0.0, 100.0)),
            "assignment_completion_pct": float(np.clip(assignment_pct, 0.0, 100.0)),
            "engagement_score": float(np.clip(events * 4.0 + clubs * 10.0 + hackathons * 15.0, 0.0, 100.0)),
            "certifications_norm": float(np.clip(certifications * 25.0, 0.0, 100.0)),
            "technical_score": float(np.clip(technical, 0.0, 100.0)),
            "softskill_score": float(np.clip(softskill, 0.0, 100.0)),
            "feedback_norm": float(np.clip(((faculty_rating - 1.0) / 4.0) * 50.0 + ((satisfaction - 1.0) / 4.0) * 50.0, 0.0, 100.0))
        }
        return norm

def compute_subscores(norm_df_or_dict):
    """
    Compute Academic Health (0-100) and Placement Readiness (0-100) sub-scores,
    plus attendance, LMS/engagement, and skills/feedback composites.
    """
    is_df = isinstance(norm_df_or_dict, pd.DataFrame)
    d = norm_df_or_dict

    # Academic Health: 70% CGPA + 30% Backlog clearance
    acad_health = 0.70 * d["cgpa_norm"] + 0.30 * d["backlogs_norm"]
    
    # Placement Readiness: 40% Coding + 35% Aptitude + 25% Mock Interviews
    place_ready = 0.40 * d["coding"] + 0.35 * d["aptitude"] + 0.25 * d["mock_interviews_norm"]
    
    # Attendance subscore: 100% Attendance
    att_sub = d["attendance_pct"]
    
    # LMS / Engagement subscore: 40% Assignments + 35% LMS Logins + 25% Engagement
    lms_sub = 0.40 * d["assignment_completion_pct"] + 0.35 * d["lms_logins_norm"] + 0.25 * d["engagement_score"]
    
    # Skills / Feedback subscore: 35% Technical + 25% Softskill + 20% Certs + 20% Feedback
    skills_sub = 0.35 * d["technical_score"] + 0.25 * d["softskill_score"] + 0.20 * d["certifications_norm"] + 0.20 * d["feedback_norm"]

    # Success Score formula as defined in brief:
    # Academic 35% + Attendance 20% + Placement 20% + LMS 15% + Skills/Feedback 10%
    success_score = (
        WEIGHTS["academic"] * acad_health +
        WEIGHTS["attendance"] * att_sub +
        WEIGHTS["placement"] * place_ready +
        WEIGHTS["lms_engagement"] * lms_sub +
        WEIGHTS["skills_feedback"] * skills_sub
    )

    if is_df:
        res = pd.DataFrame(index=d.index)
        res["academic_health"] = acad_health.round(1)
        res["placement_readiness"] = place_ready.round(1)
        res["attendance_subscore"] = att_sub.round(1)
        res["lms_engagement_subscore"] = lms_sub.round(1)
        res["skills_feedback_subscore"] = skills_sub.round(1)
        res["success_score"] = success_score.round(1)
        return res
    else:
        return {
            "academic_health": round(float(acad_health), 1),
            "placement_readiness": round(float(place_ready), 1),
            "attendance_subscore": round(float(att_sub), 1),
            "lms_engagement_subscore": round(float(lms_sub), 1),
            "skills_feedback_subscore": round(float(skills_sub), 1),
            "success_score": round(float(success_score), 1)
        }

def compute_indicator_drivers(norm_row, cohort_means):
    """
    Calculate indicator drivers: impact = weight x (student value - cohort average).
    Returns top 3 drags (negative drivers) and top 2 strengths (positive drivers).
    """
    drivers = []
    for col, (label, weight) in DRIVER_INDICATORS.items():
        val = norm_row.get(col, 0.0)
        mean_val = cohort_means.get(col, 50.0)
        diff = val - mean_val
        impact = round(float(weight * diff), 2)
        drivers.append({"col": col, "label": label, "impact": impact, "diff": round(diff, 1)})

    # Sort drags: most negative impact first
    drags = [d for d in drivers if d["impact"] < 0]
    drags.sort(key=lambda x: x["impact"])
    top_drags_list = drags[:3]
    top_drags_str = ", ".join([f"{d['label']} ({d['impact']:+.1f} pts)" for d in top_drags_list]) if top_drags_list else "None"

    # Sort strengths: most positive impact first
    strengths = [d for d in drivers if d["impact"] > 0]
    strengths.sort(key=lambda x: x["impact"], reverse=True)
    top_strengths_list = strengths[:2]
    top_strengths_str = ", ".join([f"{d['label']} ({d['impact']:+.1f} pts)" for d in top_strengths_list]) if top_strengths_list else "None"

    return top_drags_str, top_strengths_str, top_drags_list, top_strengths_list

def evaluate_risks(row, trend_delta=0.0):
    """
    Evaluate multi-factor risk flags and compile plain-English analyst reasons:
    - Academic Risk: CGPA < 6.0, Attendance < 75%, 2+ Backlogs, Falling trend
    - Placement Risk: Coding < 40, No mock interviews, Final/pre-final year, Low aptitude
    """
    academic_reasons = []
    placement_reasons = []

    # Academic risk rules
    if row["cgpa"] < THRESHOLDS["cgpa_min"]:
        academic_reasons.append(f"CGPA below 6.0 ({row['cgpa']:.2f})")
    if row["attendance_pct"] < THRESHOLDS["attendance_min"]:
        academic_reasons.append(f"Attendance below 75% ({row['attendance_pct']:.1f}%)")
    if row["backlogs"] >= THRESHOLDS["backlogs_max"]:
        academic_reasons.append(f"{int(row['backlogs'])}+ active backlogs")
    if trend_delta < THRESHOLDS["trend_delta_warning"]:
        academic_reasons.append(f"Declining academic trend ({trend_delta:+.1f} pts)")

    # Placement risk rules
    if row["coding"] < THRESHOLDS["coding_min"]:
        placement_reasons.append(f"Coding proficiency below 40 ({row['coding']:.1f})")
    if row["mock_interviews"] == 0:
        placement_reasons.append("Zero mock interviews completed")
    if row["year"] in [3, 4]:
        if row["coding"] < 50 or row["aptitude"] < 55 or row["mock_interviews"] < 1:
            placement_reasons.append(f"Year {int(row['year'])} placement readiness gap")
    if row["aptitude"] < THRESHOLDS["aptitude_min"]:
        placement_reasons.append(f"Aptitude score below 50 ({row['aptitude']:.1f})")

    # Determine Academic Risk tier
    if len(academic_reasons) >= 2 or row["cgpa"] < 5.3:
        acad_risk = "High"
    elif len(academic_reasons) == 1:
        acad_risk = "Medium"
    else:
        acad_risk = "Low"

    # Determine Placement Risk tier
    if row["year"] in [3, 4] and len(placement_reasons) >= 2:
        place_risk = "High"
    elif len(placement_reasons) >= 1:
        place_risk = "Medium"
    else:
        place_risk = "Low"

    all_reasons = academic_reasons + placement_reasons
    reasons_str = " | ".join(all_reasons) if all_reasons else "Normal academic & placement standing"

    return acad_risk, place_risk, reasons_str

def calculate_trend_deltas(conn, students_df):
    """
    Compute longitudinal sub-deltas and combined trend_delta:
    1. cgpa_trend_delta: last 2 semesters of CGPA (delta scaled * 10)
    2. attendance_trend_delta: last 2 months (M3, M4) vs earlier 2 months (M1, M2)
    3. lms_trend_delta: last 4 weeks (W5-W8) vs earlier 4 weeks (W1-W4)
    4. combined trend_delta: weighted blend
    """
    # 1. CGPA sub-delta (last 2 semesters)
    cgpa_deltas = {}
    sem_df = pd.read_sql("SELECT student_id, semester, cgpa FROM semester_history ORDER BY student_id, semester", conn)
    for sid, group in sem_df.groupby("student_id"):
        # If fewer than 2 semesters of CGPA history, set cgpa_trend_delta to None / 0.0
        if len(group) >= 2:
            last_cgpa = group.iloc[-1]["cgpa"]
            prev_cgpa = group.iloc[-2]["cgpa"]
            delta = (last_cgpa - prev_cgpa) * 10.0
            cgpa_deltas[sid] = round(float(delta), 1)
        else:
            cgpa_deltas[sid] = 0.0

    # 2. Attendance sub-delta (M3, M4 vs M1, M2)
    att_deltas = {}
    att_df = pd.read_sql("SELECT student_id, month, attendance_pct FROM attendance_history ORDER BY student_id, month", conn)
    for sid, group in att_df.groupby("student_id"):
        m_early = group[group["month"].isin(["Month 1", "Month 2"])]["attendance_pct"].mean()
        m_recent = group[group["month"].isin(["Month 3", "Month 4"])]["attendance_pct"].mean()
        if pd.notna(m_recent) and pd.notna(m_early):
            delta = m_recent - m_early
        else:
            delta = 0.0
        att_deltas[sid] = round(float(delta), 1)

    # 3. LMS sub-delta (W5-W8 vs W1-W4)
    lms_deltas = {}
    lms_df = pd.read_sql("SELECT student_id, week, logins FROM lms_history ORDER BY student_id, week", conn)
    early_weeks = ["Week 1", "Week 2", "Week 3", "Week 4"]
    recent_weeks = ["Week 5", "Week 6", "Week 7", "Week 8"]
    for sid, group in lms_df.groupby("student_id"):
        w_early = group[group["week"].isin(early_weeks)]["logins"].mean()
        w_recent = group[group["week"].isin(recent_weeks)]["logins"].mean()
        if pd.notna(w_recent) and pd.notna(w_early):
            delta = w_recent - w_early
        else:
            delta = 0.0
        lms_deltas[sid] = round(float(delta), 1)

    # Assemble into DataFrame
    res = pd.DataFrame(index=students_df.index)
    res["cgpa_trend_delta"] = students_df["student_id"].map(lambda sid: cgpa_deltas.get(sid, 0.0))
    res["attendance_trend_delta"] = students_df["student_id"].map(lambda sid: att_deltas.get(sid, 0.0))
    res["lms_trend_delta"] = students_df["student_id"].map(lambda sid: lms_deltas.get(sid, 0.0))

    # Combined trend_delta: 40% CGPA + 35% Attendance + 25% LMS (scaled * 4 to match 0-100 scale)
    combined = (
        0.40 * res["cgpa_trend_delta"] +
        0.35 * res["attendance_trend_delta"] +
        0.25 * (res["lms_trend_delta"] * 4.0)
    ).round(1)
    res["trend_delta"] = combined
    return res

def segment_students(df):
    """
    Assign both rule-based behavioral segments and statistical K-Means clusters.
    """
    rule_segments = []
    for _, row in df.iterrows():
        acad = row["academic_health"]
        place = row["placement_readiness"]
        att = row["attendance_pct"]
        cgpa = row["cgpa"]
        backlogs = row["backlogs"]
        lms = row["lms_logins_avg"]
        assign = row["assignment_completion_pct"]
        score = row["success_score"]

        if score >= 84.0 and acad >= 80.0 and place >= 75.0:
            rule_segments.append(SEGMENTS["STARS"])
        elif acad >= 70.0 and place < 50.0:
            rule_segments.append(SEGMENTS["HIGH_ACAD_LOW_PLACE"])
        elif att < 70.0 or lms < 5.0 or assign < 55.0:
            rule_segments.append(SEGMENTS["DISENGAGING"])
        elif att >= 75.0 and (cgpa < 6.5 or backlogs > 0):
            rule_segments.append(SEGMENTS["SILENT_STRUGGLERS"])
        else:
            rule_segments.append(SEGMENTS["STEADY"])

    # K-Means clustering (4 clusters) with human-readable labels
    features = df[["academic_health", "placement_readiness", "attendance_pct", "lms_logins_avg"]].copy()
    scaler = StandardScaler()
    scaled_feats = scaler.fit_transform(features)
    kmeans = KMeans(n_clusters=4, random_state=42, n_init=10)
    clusters = kmeans.fit_predict(scaled_feats)

    # Label clusters based on center characteristics
    cluster_centers = pd.DataFrame(scaler.inverse_transform(kmeans.cluster_centers_), columns=features.columns)
    cluster_labels_map = {}
    for c_id, row in cluster_centers.iterrows():
        if row["academic_health"] >= 80 and row["placement_readiness"] >= 75:
            label = "High Achievers"
        elif row["academic_health"] < 60 or row["attendance_pct"] < 65:
            label = "Critical Support Required"
        elif row["academic_health"] >= 70 and row["placement_readiness"] < 60:
            label = "Academic Focused / Skill Gap"
        else:
            label = "Consistent Progress"
        cluster_labels_map[c_id] = f"Cluster {c_id}: {label}"

    cluster_labels = [cluster_labels_map[c] for c in clusters]
    return rule_segments, cluster_labels

def calculate_data_confidence(df):
    """
    Calculate data confidence score (0-100) based on % of imputed attributes.
    16 core input attributes. 0 imputations = 100% confidence.
    """
    total_fields = 16.0
    imputed_counts = df.get("imputed_field_count", pd.Series(0, index=df.index))
    confidence = (100.0 - (imputed_counts / total_fields) * 100.0).clip(50.0, 100.0).round(1)
    return confidence

def train_early_warning_classifier(df):
    """
    Train a simple Logistic Regression classifier to output early-warning probability.
    Rule flags remain the primary signal; this provides supplementary probability.
    """
    feature_cols = [
        "cgpa", "backlogs", "attendance_pct", "coding", "aptitude",
        "mock_interviews", "lms_logins_avg", "assignment_completion_pct"
    ]
    X = df[feature_cols].copy()
    
    # Ground truth proxy: either High academic or High placement risk
    y = ((df["academic_risk"] == "High") | (df["placement_risk"] == "High")).astype(int)

    if y.nunique() < 2:
        return pd.Series(0.1, index=df.index)

    model = LogisticRegression(max_iter=1000, random_state=42)
    model.fit(X, y)
    probs = model.predict_proba(X)[:, 1]
    return np.round(probs, 3)

def score_student(indicators_dict, cohort_means=None):
    """
    What-If Simulator interface: scores a single student from an indicator dictionary.
    Returns subscores, drivers, risk flags, and predicted impact.
    """
    norm = normalize_metrics(indicators_dict)
    sub = compute_subscores(norm)
    
    if cohort_means is None:
        cohort_means = {
            "cgpa_norm": 70.0, "backlogs_norm": 85.0, "attendance_pct": 78.0,
            "coding": 58.0, "aptitude": 62.0, "mock_interviews_norm": 40.0,
            "lms_logins_norm": 50.0, "assignment_completion_pct": 75.0,
            "technical_score": 65.0, "softskill_score": 68.0, "feedback_norm": 70.0
        }

    drags_str, strengths_str, drags_list, strengths_list = compute_indicator_drivers(norm, cohort_means)
    
    # Dummy row for risk evaluation
    row = {
        "cgpa": indicators_dict.get("cgpa", 7.0),
        "attendance_pct": indicators_dict.get("attendance_pct", 75.0),
        "backlogs": indicators_dict.get("backlogs", 0),
        "coding": indicators_dict.get("coding", 60.0),
        "aptitude": indicators_dict.get("aptitude", 60.0),
        "mock_interviews": indicators_dict.get("mock_interviews", 1),
        "year": indicators_dict.get("year", 3)
    }
    acad_risk, place_risk, reasons = evaluate_risks(row, trend_delta=indicators_dict.get("trend_delta", 0.0))

    return {
        "success_score": sub["success_score"],
        "academic_health": sub["academic_health"],
        "placement_readiness": sub["placement_readiness"],
        "attendance_subscore": sub["attendance_subscore"],
        "lms_engagement_subscore": sub["lms_engagement_subscore"],
        "skills_feedback_subscore": sub["skills_feedback_subscore"],
        "academic_risk": acad_risk,
        "placement_risk": place_risk,
        "risk_reasons": reasons,
        "top_drags": drags_str,
        "top_strengths": strengths_str,
        "drags_list": drags_list,
        "strengths_list": strengths_list
    }

def score_all(verbose=True):
    """
    Orchestrate full cohort scoring pipeline and save to SQLite `students_scored`.
    """
    if verbose:
        print("Scoring all students from `students_unified`...")

    conn = sqlite3.connect(DB_PATH)
    unified = pd.read_sql("SELECT * FROM students_unified", conn)

    if unified.empty:
        raise ValueError("Table 'students_unified' is empty. Ingest data first.")

    # 1. Normalise indicators
    norm_df = normalize_metrics(unified)
    
    # 2. Compute Subscores and Success Scores
    sub_df = compute_subscores(norm_df)
    
    # Combine normalized and subscores with demographic info
    scored = unified.copy()
    scored["success_score"] = sub_df["success_score"]
    scored["academic_health"] = sub_df["academic_health"]
    scored["placement_readiness"] = sub_df["placement_readiness"]

    # 3. Longitudinal Trend Deltas (3 sub-deltas + combined)
    trend_res = calculate_trend_deltas(conn, scored)
    scored["cgpa_trend_delta"] = trend_res["cgpa_trend_delta"]
    scored["attendance_trend_delta"] = trend_res["attendance_trend_delta"]
    scored["lms_trend_delta"] = trend_res["lms_trend_delta"]
    scored["trend_delta"] = trend_res["trend_delta"]

    # 4. Multi-factor Risk Evaluation
    acad_risks, place_risks, all_reasons = [], [], []
    for idx, row in scored.iterrows():
        t_delta = row["trend_delta"]
        ar, pr, r_str = evaluate_risks(row, t_delta)
        acad_risks.append(ar)
        place_risks.append(pr)
        all_reasons.append(r_str)
    
    scored["academic_risk"] = acad_risks
    scored["placement_risk"] = place_risks
    scored["risk_reasons"] = all_reasons

    # 5. Indicator Drivers (Top Drags & Strengths)
    cohort_means = norm_df.mean().to_dict()
    top_drags, top_strengths = [], []
    for idx, row in norm_df.iterrows():
        drags_s, strengths_s, _, _ = compute_indicator_drivers(row.to_dict(), cohort_means)
        top_drags.append(drags_s)
        top_strengths.append(strengths_s)

    scored["top_drags"] = top_drags
    scored["top_strengths"] = top_strengths

    # 6. Behavioral Segmentation and Clustering
    rule_segs, cluster_lbls = segment_students(scored)
    scored["segment"] = rule_segs
    scored["cluster_label"] = cluster_lbls

    # 7. Data Confidence & Low Confidence Flag (< 70%)
    scored["data_confidence"] = calculate_data_confidence(scored)
    scored["low_confidence"] = (scored["data_confidence"] < 70.0).astype(int)

    # 8. Early Warning Classifier Probability
    scored["early_warning_prob"] = train_early_warning_classifier(scored)

    # 9. Priority Ranking for Faculty Intervention Queue (Risk Triage Score)
    # risk_triage_score = (100 - success_score) + 25*(AcadRisk == 'High') + 20*(PlaceRisk == 'High') + 10*(PlaceRisk == 'Medium') + max(0, -trend_delta)*2.0
    risk_triage_score = (
        (100.0 - scored["success_score"]) +
        (scored["academic_risk"] == "High").astype(int) * 25.0 +
        (scored["placement_risk"] == "High").astype(int) * 20.0 +
        (scored["placement_risk"] == "Medium").astype(int) * 10.0 +
        np.maximum(0.0, -scored["trend_delta"]) * 2.0
    ).round(1)
    scored["risk_triage_score"] = risk_triage_score

    # Save to SQLite table `students_scored`
    scored.to_sql("students_scored", conn, if_exists="replace", index=False)
    conn.close()

    if verbose:
        print(f"Table 'students_scored' successfully created: {len(scored)} records.")
        print("\nTop 10 Students by Faculty Risk Triage Score:")
        top10 = scored.sort_values(by="risk_triage_score", ascending=False).head(10)
        display_cols = [
            "student_id", "name", "department", "year", "success_score",
            "academic_risk", "placement_risk", "risk_triage_score", "risk_reasons"
        ]
        print(top10[display_cols].to_string(index=False))

    return scored

def get_cohort_summary_kpis(conn=None) -> dict:
    """
    Computes cohort-level summary KPIs directly from the SQLite database:
    - total_students
    - mean_success_score
    - academic_risk_high_count
    - placement_risk_high_count
    - low_confidence_count
    - insight_sentence
    """
    close_after = False
    if conn is None:
        conn = sqlite3.connect(DB_PATH)
        close_after = True

    df = pd.read_sql(
        "SELECT student_id, success_score, department, year, academic_risk, placement_risk, low_confidence FROM students_scored",
        conn
    )
    if close_after:
        conn.close()

    total_students = int(len(df))
    mean_score = float(df["success_score"].mean()) if total_students > 0 else 0.0
    acad_high = int((df["academic_risk"] == "High").sum())
    place_high = int((df["placement_risk"] == "High").sum())
    low_conf = int((df["low_confidence"] == 1).sum())

    # Dynamic insight statement: "N students below score 50; X% concentrated in <department/year>"
    # Strictly claim concentration ONLY when the group's share of low scorers exceeds its share of all students
    below_50 = df[df["success_score"] < 50.0]
    n_below = int(len(below_50))
    if n_below > 0:
        # Find group with highest excess share: (share_of_low_scorers - share_of_all_students)
        groups = []
        for (dept, yr), g in df.groupby(["department", "year"]):
            g_total = len(g)
            g_below = len(below_50[(below_50["department"] == dept) & (below_50["year"] == yr)])
            share_total = (g_total / total_students) * 100.0
            share_below = (g_below / n_below) * 100.0
            diff = share_below - share_total
            groups.append({
                "name": f"{dept} Year {int(yr)}",
                "below_count": g_below,
                "total_count": g_total,
                "share_below": share_below,
                "share_total": share_total,
                "diff": diff
            })
        
        # Sort by excess share of low scorers over total cohort share
        top_group = max(groups, key=lambda x: x["diff"])
        
        if top_group["diff"] > 0:
            insight_sentence = (
                f"{n_below} students below score 50; {top_group['below_count']} ({top_group['share_below']:.1f}%) "
                f"concentrated in {top_group['name']} (group represents {top_group['total_count']} of {total_students} students, {top_group['share_total']:.1f}%)."
            )
        else:
            insight_sentence = f"{n_below} students below score 50, evenly distributed across cohort departments and years."
    else:
        insight_sentence = "All students maintain success scores at or above baseline 50."

    return {
        "total_students": total_students,
        "mean_success_score": round(mean_score, 2),
        "academic_risk_high_count": acad_high,
        "placement_risk_high_count": place_high,
        "low_confidence_count": low_conf,
        "insight_sentence": insight_sentence
    }

def get_department_year_heatmap(conn=None) -> dict:
    """
    Returns department x year mean success score matrix and count matrix.
    Includes cell note flag when sample size n < 15.
    """
    close_after = False
    if conn is None:
        conn = sqlite3.connect(DB_PATH)
        close_after = True

    df = pd.read_sql("SELECT department, year, success_score FROM students_scored", conn)
    if close_after:
        conn.close()

    df["year"] = df["year"].astype(int)
    mean_pivot = df.pivot_table(index="department", columns="year", values="success_score", aggfunc="mean").round(2)
    count_pivot = df.pivot_table(index="department", columns="year", values="success_score", aggfunc="count").fillna(0).astype(int)

    # Format annotations: "Score\n(n=Count)*" if count < 15
    annotations = []
    has_small_sample = False
    for dept in mean_pivot.index:
        row_ann = []
        for yr in mean_pivot.columns:
            m_val = mean_pivot.loc[dept, yr]
            c_val = count_pivot.loc[dept, yr]
            flag = "*" if c_val < 15 else ""
            if c_val < 15:
                has_small_sample = True
            row_ann.append(f"{m_val:.1f}{flag}<br><span style='font-size:10px;'>n={c_val}</span>")
        annotations.append(row_ann)

    return {
        "departments": list(mean_pivot.index),
        "years": [f"Year {y}" for y in mean_pivot.columns],
        "years_raw": list(mean_pivot.columns),
        "mean_matrix": mean_pivot.values.tolist(),
        "count_matrix": count_pivot.values.tolist(),
        "annotations": annotations,
        "has_small_sample": has_small_sample,
        "mean_df": mean_pivot,
        "count_df": count_pivot
    }

def get_segment_distribution(conn=None) -> pd.DataFrame:
    """
    Returns rule-based segment distribution counts and percentages.
    """
    close_after = False
    if conn is None:
        conn = sqlite3.connect(DB_PATH)
        close_after = True

    df = pd.read_sql("SELECT segment, count(*) as count FROM students_scored GROUP BY segment ORDER BY count DESC", conn)
    if close_after:
        conn.close()

    total = df["count"].sum()
    df["percentage"] = (df["count"] / total * 100.0).round(1)
    return df

def get_top_triage_students(limit: int = 10, conn=None) -> pd.DataFrame:
    """
    Returns top N students ordered by faculty risk triage score.
    """
    close_after = False
    if conn is None:
        conn = sqlite3.connect(DB_PATH)
        close_after = True

    query = """
        SELECT student_id, name, department, year, success_score, risk_triage_score,
               academic_risk, placement_risk, risk_reasons
        FROM students_scored
        ORDER BY risk_triage_score DESC
        LIMIT ?
    """
    df = pd.read_sql(query, conn, params=(limit,))
    if close_after:
        conn.close()

    df["year"] = df["year"].astype(int)
    df["success_score"] = df["success_score"].round(1)
    df["risk_triage_score"] = df["risk_triage_score"].round(1)
    return df

def get_cohort_scores_distribution(conn=None) -> pd.Series:
    """
    Returns the raw series of success scores for histogram plotting.
    """
    close_after = False
    if conn is None:
        conn = sqlite3.connect(DB_PATH)
        close_after = True

    df = pd.read_sql("SELECT success_score FROM students_scored", conn)
    if close_after:
        conn.close()

    return df["success_score"]

def get_trends_data(scoped_student_ids: list = None, conn=None) -> dict:
    """
    Computes aggregated trend datasets for longitudinal analytics:
    - semester_cgpa_by_cohort: mean CGPA per admission year cohort (years 1..4) across valid semesters
    - monthly_attendance_by_dept: mean attendance across 4 months per department
    - weekly_lms_by_dept: mean logins across 8 weeks per department
    - department_comparison: summary comparison table with right-aligned metrics and student counts
    - insight_title: dynamic statement of which department's attendance fell most over the last 2 months
    """
    close_after = False
    if conn is None:
        conn = sqlite3.connect(DB_PATH)
        close_after = True

    # 1. Base scoped students
    if scoped_student_ids is not None:
        placeholders = ",".join("?" for _ in scoped_student_ids)
        query = f"SELECT student_id, department, year, cgpa, attendance_pct, lms_logins_avg, assignment_completion_pct FROM students_scored WHERE student_id IN ({placeholders})"
        students_df = pd.read_sql(query, conn, params=list(scoped_student_ids))
    else:
        students_df = pd.read_sql(
            "SELECT student_id, department, year, cgpa, attendance_pct, lms_logins_avg, assignment_completion_pct FROM students_scored",
            conn
        )

    if students_df.empty:
        if close_after:
            conn.close()
        return {
            "insight_title": "No student records available in scope.",
            "semester_cgpa_by_cohort": pd.DataFrame(),
            "monthly_attendance_by_dept": pd.DataFrame(),
            "weekly_lms_by_dept": pd.DataFrame(),
            "department_comparison": pd.DataFrame()
        }

    valid_sids = set(students_df["student_id"])

    # 2. Semester CGPA trend by admission year cohort (not pooled)
    sem_raw = pd.read_sql("SELECT student_id, semester, cgpa FROM semester_history WHERE semester IS NOT NULL", conn)
    sem_df = sem_raw[sem_raw["student_id"].isin(valid_sids)].copy()
    sem_df = pd.merge(sem_df, students_df[["student_id", "year"]], on="student_id")
    # Only keep completed or enrolled semesters for each cohort (semester <= year * 2)
    sem_df = sem_df[sem_df["semester"] <= sem_df["year"] * 2]
    sem_piv = sem_df.pivot_table(index="year", columns="semester", values="cgpa", aggfunc="mean").round(2)

    # 3. Monthly Attendance by Department (4 months)
    att_raw = pd.read_sql("SELECT student_id, month, attendance_pct FROM attendance_history WHERE month IS NOT NULL", conn)
    att_df = att_raw[att_raw["student_id"].isin(valid_sids)].copy()
    att_df = pd.merge(att_df, students_df[["student_id", "department"]], on="student_id")
    att_piv = att_df.pivot_table(index="department", columns="month", values="attendance_pct", aggfunc="mean").round(2)
    
    # Ensure standard month column order
    ordered_months = [m for m in ["Month 1", "Month 2", "Month 3", "Month 4"] if m in att_piv.columns]
    att_piv = att_piv[ordered_months]

    # Insight title calculation:
    # Only claim a decline if change is >= 2.0 percentage points (attendance) or >= 0.3 (CGPA).
    # Otherwise show "Attendance is stable across departments (range X to Y%)".
    insight_title = "Attendance is stable across departments."
    if "Month 2" in att_piv.columns and "Month 4" in att_piv.columns:
        drops = (att_piv["Month 4"] - att_piv["Month 2"]).round(2)
        worst_dept = drops.idxmin()
        worst_delta = drops.min()
        m2_val = att_piv.loc[worst_dept, "Month 2"]
        m4_val = att_piv.loc[worst_dept, "Month 4"]
        
        all_m4 = att_piv["Month 4"]
        range_min = all_m4.min()
        range_max = all_m4.max()

        if worst_delta <= -2.0:
            insight_title = f"{worst_dept} department attendance declined most over the last 2 months ({worst_delta:+.2f}%, from {m2_val:.1f}% in Month 2 to {m4_val:.1f}% in Month 4)."
        else:
            insight_title = f"Attendance is stable across departments (range {range_min:.1f} to {range_max:.1f}%)."

    # 4. Weekly LMS Logins by Department (8 weeks)
    lms_raw = pd.read_sql("SELECT student_id, week, logins FROM lms_history WHERE week IS NOT NULL", conn)
    lms_df = lms_raw[lms_raw["student_id"].isin(valid_sids)].copy()
    lms_df = pd.merge(lms_df, students_df[["student_id", "department"]], on="student_id")
    lms_piv = lms_df.pivot_table(index="department", columns="week", values="logins", aggfunc="mean").round(2)
    ordered_weeks = [w for w in [f"Week {i}" for i in range(1, 9)] if w in lms_piv.columns]
    lms_piv = lms_piv[ordered_weeks]

    # Insight title & Alerts scanning across all 20 Department x Year groups
    # Flag: Attendance drop >= 2.0 pts (Month 1 to Month 4) OR LMS drop >= 15% (Weeks 1-4 mean vs Weeks 5-8 mean)
    flagged_alerts = []
    
    # Merge students with attendance and lms
    s_full = pd.merge(students_df[["student_id", "department", "year"]], att_df[["student_id", "month", "attendance_pct"]], on="student_id")
    s_lms = pd.merge(students_df[["student_id", "department", "year"]], lms_df[["student_id", "week", "logins"]], on="student_id")

    for (dept, yr), grp in students_df.groupby(["department", "year"]):
        sids = set(grp["student_id"])
        group_name = f"{dept} Year {int(yr)}"
        
        # Attendance Month 1 to Month 4
        att_sub = s_full[s_full["student_id"].isin(sids)]
        m1_m = att_sub[att_sub["month"] == "Month 1"]["attendance_pct"].mean()
        m4_m = att_sub[att_sub["month"] == "Month 4"]["attendance_pct"].mean()
        att_drop = round(m4_m - m1_m, 2) if (pd.notna(m1_m) and pd.notna(m4_m)) else 0.0

        # LMS Weeks 1-4 vs Weeks 5-8
        lms_sub = s_lms[s_lms["student_id"].isin(sids)]
        w1_4 = lms_sub[lms_sub["week"].isin(["Week 1", "Week 2", "Week 3", "Week 4"])]["logins"].mean()
        w5_8 = lms_sub[lms_sub["week"].isin(["Week 5", "Week 6", "Week 7", "Week 8"])]["logins"].mean()
        lms_drop_pct = round(((w5_8 - w1_4) / w1_4) * 100.0, 1) if (pd.notna(w1_4) and w1_4 > 0 and pd.notna(w5_8)) else 0.0

        flags = []
        if att_drop <= -2.0:
            flags.append(f"Attendance declined {abs(att_drop):.1f} pts ({m1_m:.1f}% in M1 to {m4_m:.1f}% in M4)")
        if lms_drop_pct <= -15.0:
            flags.append(f"LMS logins dropped {abs(lms_drop_pct):.1f}% ({w1_4:.1f} W1-4 to {w5_8:.1f} W5-8)")

        if flags:
            flagged_alerts.append({
                "group": group_name,
                "dept": dept,
                "year": int(yr),
                "att_drop": att_drop,
                "lms_drop_pct": lms_drop_pct,
                "reasons": "; ".join(flags)
            })

    # Compose insight title from flagged cohorts
    if flagged_alerts:
        alert_names = [f"{a['group']} ({a['reasons']})" for a in flagged_alerts]
        insight_title = f"Multi-Cohort Alert: Significant engagement decline detected in {', '.join(alert_names)}."
    else:
        all_m4 = att_piv["Month 4"] if "Month 4" in att_piv.columns else pd.Series()
        r_min = all_m4.min() if not all_m4.empty else 0.0
        r_max = all_m4.max() if not all_m4.empty else 0.0
        insight_title = f"Attendance is stable across departments (range {r_min:.1f} to {r_max:.1f}%)."

    # 5. Department comparison table
    dept_comp = students_df.groupby("department").agg(
        n=("student_id", "count"),
        mean_cgpa=("cgpa", "mean"),
        mean_attendance=("attendance_pct", "mean"),
        mean_lms=("lms_logins_avg", "mean"),
        mean_assignment=("assignment_completion_pct", "mean")
    ).round(2).reset_index()

    if close_after:
        conn.close()

    return {
        "insight_title": insight_title,
        "flagged_alerts": flagged_alerts,
        "semester_cgpa_by_cohort": sem_piv,
        "monthly_attendance_by_dept": att_piv,
        "weekly_lms_by_dept": lms_piv,
        "department_comparison": dept_comp
    }

if __name__ == "__main__":
    score_all(verbose=True)
