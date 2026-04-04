"""
ClaimIQ - Production Fraud Detection Engine
============================================
Dual-logic system: Hard Rules (instant rejection) + Soft Rules (weighted scoring)
Plus ML fraud probability integration (0–1 scale).

Architecture:
  1. HARD RULES — non-breakable, any failure = instant REJECT
  2. SOFT RULES — weighted score, start at 100, add/subtract points
  3. ML MODEL   — Random Forest probability 0–1
  4. COMBINED    — Hard override > ML thresholds > Soft score thresholds
"""
import os
import json
import pickle
import numpy as np
from datetime import datetime, date
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, asdict
from backend.core.config import settings


# ═══════════════════════════════════════════════════════════════════════
# HARD RULES — Any single failure → instant REJECT
# ═══════════════════════════════════════════════════════════════════════

HARD_RULES = [
    {
        "id": "HARD_001",
        "name": "Policy Expired",
        "description": "Policy end date has passed — claim is not covered",
    },
    {
        "id": "HARD_002",
        "name": "Claim Exceeds Insured Limit",
        "description": "Claim amount exceeds the maximum policy coverage limit",
    },
    {
        "id": "HARD_003",
        "name": "Missing Mandatory Documents",
        "description": "Required supporting documents have not been uploaded",
    },
    {
        "id": "HARD_004",
        "name": "Duplicate Claim ID",
        "description": "A claim with this reference already exists in the system",
    },
    {
        "id": "HARD_005",
        "name": "Fake Signature/Stamp Detected",
        "description": "Image analysis detected missing or forged signature/stamp on documents",
    },
]


def evaluate_hard_rules(
    claim_amount: float,
    policy_limit: float,
    policy_end_str: Optional[str],
    uploaded_doc_types: List[str],
    required_doc_types: List[str],
    is_duplicate: bool,
    signature_stamp_failed: bool,
) -> Tuple[Optional[str], List[Dict]]:
    """
    Evaluate all hard rules. Returns:
      (violated_rule_id or None, list_of_rule_results)
    If violated_rule_id is not None, claim must be REJECTED immediately.
    """
    results = []

    # HARD_001: Policy expired
    policy_expired = False
    if policy_end_str:
        try:
            policy_end = datetime.strptime(policy_end_str, "%Y-%m-%d").date()
            policy_expired = policy_end < datetime.utcnow().date()
        except Exception:
            pass

    results.append({
        "rule_id": "HARD_001", "name": "Policy Expired",
        "triggered": policy_expired,
        "description": "Policy end date has passed" if policy_expired else "Policy is active",
    })

    # HARD_002: Claim > insured limit
    over_limit = claim_amount > policy_limit
    results.append({
        "rule_id": "HARD_002", "name": "Claim Exceeds Insured Limit",
        "triggered": over_limit,
        "description": f"Claim ${claim_amount:,.0f} exceeds limit ${policy_limit:,.0f}" if over_limit
                       else f"Claim ${claim_amount:,.0f} within limit ${policy_limit:,.0f}",
    })

    # HARD_003: Missing mandatory documents
    # NOTE: This is tracked but NOT a hard rejection — docs may be uploaded
    # after claim creation in the 2-step portal flow. Missing docs are handled
    # as a soft concern that leads to manual_review, not instant rejection.
    missing = [d for d in required_doc_types if d not in uploaded_doc_types]
    results.append({
        "rule_id": "HARD_003", "name": "Missing Mandatory Documents",
        "triggered": False,  # Never hard-reject for missing docs
        "description": f"Missing: {', '.join(missing)}" if missing
                       else "All mandatory documents present",
    })

    # HARD_004: Duplicate claim
    results.append({
        "rule_id": "HARD_004", "name": "Duplicate Claim ID",
        "triggered": is_duplicate,
        "description": "Duplicate claim reference detected" if is_duplicate
                       else "Unique claim reference",
    })

    # HARD_005: Fake signature/stamp
    results.append({
        "rule_id": "HARD_005", "name": "Fake Signature/Stamp Detected",
        "triggered": signature_stamp_failed,
        "description": "Signature or stamp forgery/absence detected" if signature_stamp_failed
                       else "Signature/stamp check passed",
    })

    # Find first violation
    for r in results:
        if r["triggered"]:
            return r["rule_id"], results

    return None, results


# ═══════════════════════════════════════════════════════════════════════
# SOFT RULES — Weighted scoring, base = 100
# ═══════════════════════════════════════════════════════════════════════

SOFT_RULES = [
    {"id": "SOFT_001", "name": "Claim Within 30 Days",          "points": +20, "type": "positive"},
    {"id": "SOFT_002", "name": "Trusted Provider",              "points": +15, "type": "positive"},
    {"id": "SOFT_003", "name": "Repeated Claimant",             "points": -25, "type": "negative"},
    {"id": "SOFT_004", "name": "High Claim Amount",             "points": -20, "type": "negative"},
    {"id": "SOFT_005", "name": "Inconsistent Dates",            "points": -30, "type": "negative"},
    {"id": "SOFT_006", "name": "Round Number Amount",           "points": -10, "type": "negative"},
    {"id": "SOFT_007", "name": "Weekend Incident",              "points":  -5, "type": "negative"},
    {"id": "SOFT_008", "name": "Same-Day Filing",               "points": -15, "type": "negative"},
    {"id": "SOFT_009", "name": "Prior Fraud on Account",        "points": -30, "type": "negative"},
    {"id": "SOFT_010", "name": "Late Reporting (>30 days)",     "points": -10, "type": "negative"},
    {"id": "SOFT_011", "name": "OCR Amount Mismatch",           "points": -20, "type": "negative"},
    {"id": "SOFT_012", "name": "New Policy (<30 days)",         "points": -15, "type": "negative"},
]

# Trusted providers for SOFT_002
TRUSTED_PROVIDERS = [
    "apollo", "fortis", "max healthcare", "medanta", "aiims",
    "manipal", "narayana", "columbia asia", "lilavati", "kokilaben",
    "tata memorial", "breach candy", "hinduja", "jaslok",
    "maruti", "toyota", "honda", "hyundai", "tata motors",
    "authorized service center", "company workshop",
]


def evaluate_soft_rules(
    claim_amount: float,
    policy_limit: float,
    prior_claims: int,
    prior_fraud_flags: int,
    incident_date_str: str,
    submission_date: Optional[datetime] = None,
    policy_start_str: Optional[str] = None,
    ocr_amount: Optional[float] = None,
    ocr_date: Optional[str] = None,
    provider_name: Optional[str] = None,
) -> Tuple[float, List[Dict]]:
    """
    Evaluate soft rules and return (score, rule_results).
    Score starts at 100 and is adjusted by rule points.
    """
    score = 100.0
    results = []
    submission = submission_date or datetime.utcnow()

    try:
        incident_date = datetime.strptime(incident_date_str, "%Y-%m-%d").date()
    except Exception:
        incident_date = date.today()

    days_since = (submission.date() - incident_date).days

    for rule in SOFT_RULES:
        triggered = False
        detail = ""

        if rule["id"] == "SOFT_001":
            triggered = 0 <= days_since <= 30
            detail = f"Filed {days_since} days after incident"

        elif rule["id"] == "SOFT_002":
            if provider_name:
                triggered = any(tp in provider_name.lower() for tp in TRUSTED_PROVIDERS)
                detail = f"Provider: {provider_name}" + (" (trusted)" if triggered else " (unknown)")
            else:
                detail = "No provider name extracted"

        elif rule["id"] == "SOFT_003":
            triggered = prior_claims >= 3
            detail = f"Prior claims: {prior_claims}"

        elif rule["id"] == "SOFT_004":
            ratio = claim_amount / max(policy_limit, 1)
            triggered = ratio >= 0.8
            detail = f"Claim is {ratio*100:.0f}% of policy limit"

        elif rule["id"] == "SOFT_005":
            if ocr_date and incident_date_str:
                try:
                    ocr_d = datetime.strptime(ocr_date, "%Y-%m-%d").date()
                    triggered = abs((ocr_d - incident_date).days) > 30
                    detail = f"OCR date {ocr_date} vs incident {incident_date_str}"
                except Exception:
                    detail = "Could not parse OCR date"
            else:
                detail = "No OCR date to compare"

        elif rule["id"] == "SOFT_006":
            triggered = claim_amount > 0 and claim_amount % 1000 == 0
            detail = f"Amount: ${claim_amount:,.0f}"

        elif rule["id"] == "SOFT_007":
            triggered = incident_date.weekday() >= 5
            detail = f"Incident on {incident_date.strftime('%A')}"

        elif rule["id"] == "SOFT_008":
            triggered = days_since == 0
            detail = f"Filed same day as incident" if triggered else f"Filed {days_since} days later"

        elif rule["id"] == "SOFT_009":
            triggered = prior_fraud_flags > 0
            detail = f"Prior fraud flags: {prior_fraud_flags}"

        elif rule["id"] == "SOFT_010":
            triggered = days_since > 30
            detail = f"Reported {days_since} days after incident"

        elif rule["id"] == "SOFT_011":
            if ocr_amount is not None and claim_amount > 0:
                diff_pct = abs(ocr_amount - claim_amount) / claim_amount
                triggered = diff_pct > 0.15
                detail = f"OCR amount ${ocr_amount:,.0f} vs claimed ${claim_amount:,.0f} ({diff_pct*100:.0f}% diff)"
            else:
                detail = "No OCR amount to compare"

        elif rule["id"] == "SOFT_012":
            if policy_start_str:
                try:
                    ps = datetime.strptime(policy_start_str, "%Y-%m-%d").date()
                    policy_age = (incident_date - ps).days
                    triggered = policy_age < 30
                    detail = f"Policy age: {policy_age} days"
                except Exception:
                    detail = "Could not parse policy start date"
            else:
                detail = "No policy start date"

        if triggered:
            score += rule["points"]  # points are already signed (+/-)

        results.append({
            "rule_id": rule["id"],
            "rule_name": rule["name"],
            "triggered": triggered,
            "points": rule["points"] if triggered else 0,
            "detail": detail,
            "type": rule["type"],
            "severity": "high" if abs(rule["points"]) >= 25 else
                        "medium" if abs(rule["points"]) >= 15 else "low",
        })

    # Clamp score to 0–100
    score = max(0.0, min(100.0, score))
    return score, results


# ═══════════════════════════════════════════════════════════════════════
# ML FRAUD MODEL — Returns probability 0–1
# ═══════════════════════════════════════════════════════════════════════

def get_ml_fraud_probability(features: Dict) -> float:
    """
    Run the trained ML model and return fraud probability (0.0–1.0).
    Returns -1.0 if model is not available.
    """
    model_path = settings.FRAUD_MODEL_PATH
    scaler_path = model_path.replace("fraud_model.pkl", "scaler.pkl")

    if not os.path.exists(model_path):
        return -1.0

    try:
        with open(model_path, "rb") as f:
            model = pickle.load(f)

        feature_vector = np.array([[
            features.get("claim_amount", 0),
            features.get("claim_to_limit_ratio", 0),
            features.get("prior_claims", 0),
            features.get("prior_fraud_flags", 0),
            features.get("days_since_incident", 0),
            features.get("policy_age_days", 0),
            features.get("is_round_number", 0),
            features.get("is_weekend", 0),
            features.get("document_count", 0),
            features.get("ocr_mismatch", 0),
            features.get("late_reporting", 0),
        ]])

        if os.path.exists(scaler_path):
            with open(scaler_path, "rb") as f:
                scaler = pickle.load(f)
            feature_vector = scaler.transform(feature_vector)

        prob = model.predict_proba(feature_vector)[0][1]  # P(fraud)
        return round(float(prob), 4)  # 0.0 – 1.0

    except Exception as e:
        print(f"[FraudML] Model prediction error: {e}")
        return -1.0


# ── Legacy adapter (backwards compat for existing code) ──────────────
def get_ml_fraud_score(features: Dict) -> float:
    """Legacy: returns fraud score 0–100 (used by existing pipeline code)."""
    prob = get_ml_fraud_probability(features)
    if prob < 0:
        return -1.0
    return round(prob * 100, 2)


def get_final_fraud_score(rule_score: float, ml_score: float, ml_weight: float = 0.4) -> float:
    """Blend rule-based score with ML score (both 0–100 scale)."""
    if ml_score < 0:
        return rule_score
    return round((rule_score * (1 - ml_weight)) + (ml_score * ml_weight), 2)


# ═══════════════════════════════════════════════════════════════════════
# COMBINED DECISION LOGIC
# ═══════════════════════════════════════════════════════════════════════

def make_combined_decision(
    hard_rule_violated: Optional[str],
    soft_score: float,
    ml_probability: float,
    duplicate_image: bool = False,
) -> Dict:
    """
    Production decision engine combining all signals.

    Priority order:
      1. Hard rule violation → REJECT
      2. Image duplicate → REJECT
      3. ML probability > 0.8 → REJECT
      4. ML probability 0.5–0.8 → HUMAN_REVIEW
      5. Soft score < 40 → REJECT
      6. Soft score 40–70 → HUMAN_REVIEW
      7. Soft score > 70 → AUTO_APPROVE
    """
    if hard_rule_violated:
        return {
            "decision": "rejected",
            "reason": f"Hard rule violated: {hard_rule_violated}",
            "auto": True,
            "override": True,
            "trigger": "hard_rule",
        }

    if duplicate_image:
        return {
            "decision": "rejected",
            "reason": "Duplicate image detected across claims — possible resubmission fraud",
            "auto": True,
            "override": True,
            "trigger": "duplicate_image",
        }

    if ml_probability >= 0 and ml_probability >= settings.ML_REJECT_THRESHOLD:
        return {
            "decision": "rejected",
            "reason": f"ML fraud probability {ml_probability:.2f} exceeds rejection threshold ({settings.ML_REJECT_THRESHOLD})",
            "auto": True,
            "override": False,
            "trigger": "ml_reject",
        }

    if ml_probability >= 0 and ml_probability >= settings.ML_REVIEW_THRESHOLD:
        return {
            "decision": "manual_review",
            "reason": f"ML fraud probability {ml_probability:.2f} requires human review (threshold {settings.ML_REVIEW_THRESHOLD})",
            "auto": False,
            "override": False,
            "trigger": "ml_review",
        }

    if soft_score < settings.SOFT_SCORE_REJECT:
        return {
            "decision": "rejected",
            "reason": f"Soft rule score {soft_score:.0f}/100 below rejection threshold ({settings.SOFT_SCORE_REJECT})",
            "auto": True,
            "override": False,
            "trigger": "soft_reject",
        }

    if soft_score < settings.SOFT_SCORE_AUTO_APPROVE:
        return {
            "decision": "manual_review",
            "reason": f"Soft rule score {soft_score:.0f}/100 requires human review (range {settings.SOFT_SCORE_REJECT}–{settings.SOFT_SCORE_AUTO_APPROVE})",
            "auto": False,
            "override": False,
            "trigger": "soft_review",
        }

    return {
        "decision": "auto_approved",
        "reason": f"All checks passed — soft score {soft_score:.0f}/100, ML probability {ml_probability:.2f}",
        "auto": True,
        "override": False,
        "trigger": "auto_approve",
    }


# ═══════════════════════════════════════════════════════════════════════
# VERDICT HELPERS (backwards-compat + new)
# ═══════════════════════════════════════════════════════════════════════

def get_fraud_verdict(fraud_score: float) -> Dict:
    """Return human-readable verdict based on fraud score (0–100 scale)."""
    if fraud_score >= settings.FRAUD_SCORE_THRESHOLD:
        return {
            "verdict": "HIGH_RISK", "action": "HOLD_FOR_REVIEW",
            "color": "red", "icon": "🔴",
            "message": "High fraud risk detected. Claim flagged for manual investigation.",
        }
    elif fraud_score >= 40:
        return {
            "verdict": "MEDIUM_RISK", "action": "MANUAL_REVIEW",
            "color": "orange", "icon": "🟠",
            "message": "Moderate risk signals found. Adjuster review recommended.",
        }
    elif fraud_score >= 20:
        return {
            "verdict": "LOW_RISK", "action": "PROCEED_WITH_CAUTION",
            "color": "yellow", "icon": "🟡",
            "message": "Minor risk indicators present. Proceed with standard verification.",
        }
    else:
        return {
            "verdict": "CLEAN", "action": "AUTO_APPROVE",
            "color": "green", "icon": "🟢",
            "message": "No significant fraud signals. Eligible for STP auto-approval.",
        }


# ── Legacy evaluate_fraud_rules ──────────────────────────────────────
# Kept for backward compatibility with existing STP engine

@dataclass
class FraudRuleResult:
    rule_id: str
    rule_name: str
    triggered: bool
    severity: str
    score_impact: float
    description: str


def evaluate_fraud_rules(
    claim_amount: float,
    policy_limit: float,
    prior_claim_count: int,
    prior_fraud_flags: int,
    incident_date_str: str,
    submission_date: Optional[datetime] = None,
    policy_start_str: Optional[str] = None,
    ocr_amount: Optional[float] = None,
) -> Tuple[float, List[FraudRuleResult]]:
    """Legacy 12-rule evaluator — wraps the new soft rules for backward compat."""
    soft_score, soft_results = evaluate_soft_rules(
        claim_amount=claim_amount,
        policy_limit=policy_limit,
        prior_claims=prior_claim_count,
        prior_fraud_flags=prior_fraud_flags,
        incident_date_str=incident_date_str,
        submission_date=submission_date,
        policy_start_str=policy_start_str,
        ocr_amount=ocr_amount,
    )

    # Convert soft score (higher=safer) to fraud score (higher=riskier)
    fraud_score = max(0, 100 - soft_score)

    legacy_results = []
    for sr in soft_results:
        if sr["triggered"]:
            legacy_results.append(FraudRuleResult(
                rule_id=sr["rule_id"],
                rule_name=sr["rule_name"],
                triggered=True,
                severity=sr["severity"],
                score_impact=abs(sr["points"]),
                description=sr["detail"],
            ))

    return fraud_score, legacy_results


# ── Training Metrics API ─────────────────────────────────────────────

def get_training_metrics() -> Optional[Dict]:
    metrics_path = os.path.join(
        os.path.dirname(settings.FRAUD_MODEL_PATH),
        "training_metrics.json"
    )
    if not os.path.exists(metrics_path):
        return None
    try:
        with open(metrics_path, "r") as f:
            return json.load(f)
    except Exception:
        return None


def get_feature_importances() -> Optional[Dict]:
    metrics = get_training_metrics()
    if metrics and "feature_importance" in metrics:
        return metrics["feature_importance"]
    return None


def is_model_available() -> bool:
    return os.path.exists(settings.FRAUD_MODEL_PATH)
