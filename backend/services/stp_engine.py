"""
ClaimIQ - Straight-Through Processing (STP) Engine
=====================================================
Production-grade 5-gate claim processing pipeline with:
  - Hard rules (instant rejection)
  - Soft rules (weighted scoring)
  - ML fraud probability (0–1)
  - Image fraud detection
  - Combined decision logic

Gate 1: Eligibility Filter
Gate 2: Document Intelligence
Gate 3: Fraud Scoring (Hard + Soft + ML + Image)
Gate 4: Risk & Coverage Calculation
Gate 5: Payout Orchestration
"""
from datetime import datetime
from typing import Dict, Tuple, Optional, List
from sqlalchemy.orm import Session

from backend.core.config import settings
from backend.models.claim import Claim
from backend.models.user import User
from backend.models.document import Document
from backend.ml.fraud_engine import (
    evaluate_hard_rules,
    evaluate_soft_rules,
    get_ml_fraud_probability,
    get_ml_fraud_score,
    get_final_fraud_score,
    get_fraud_verdict,
    make_combined_decision,
    evaluate_fraud_rules,
)


# ── Gate 1: Eligibility Filter ───────────────────────────────────────
def check_eligibility(claim: Claim, user: User) -> Tuple[bool, str]:
    """
    Returns (is_eligible, reason_if_not).
    """
    # 1. Claim amount threshold
    if claim.claim_amount > settings.STP_AMOUNT_LIMIT:
        return False, f"Claim amount ${claim.claim_amount:,.0f} exceeds STP limit of ${settings.STP_AMOUNT_LIMIT:,.0f}"

    # 2. Policy must be active (valid end date)
    if user.policy_end:
        try:
            policy_end = datetime.strptime(user.policy_end, "%Y-%m-%d").date()
            if policy_end < datetime.utcnow().date():
                return False, "Policy has expired"
        except Exception:
            pass

    # 3. No prior fraud flags
    if user.fraud_flags and user.fraud_flags > 0:
        return False, f"Account has {user.fraud_flags} prior fraud flag(s)"

    # 4. Claim type must be in STP-eligible list
    stp_eligible_types = ["auto", "health", "travel", "property"]
    if claim.claim_type not in stp_eligible_types:
        return False, f"Claim type '{claim.claim_type}' is not STP-eligible"

    # 5. No more than 1 prior claim in last 90 days (simplified: just check total count)
    if user.claim_count and user.claim_count >= 3:
        return False, f"Too many recent claims ({user.claim_count}) — requires manual review"

    return True, "All eligibility checks passed"


# ── Gate 2: Document Completeness Check ─────────────────────────────
REQUIRED_DOCS = {
    "auto":     ["police_report", "photos", "invoice"],
    "health":   ["medical_bill", "id_proof"],
    "travel":   ["id_proof", "booking_proof"],
    "property": ["photos", "invoice", "id_proof"],
}

def check_documents(claim: Claim, uploaded_doc_types: list) -> Tuple[bool, str]:
    """Check if all required documents have been uploaded."""
    required = REQUIRED_DOCS.get(claim.claim_type, ["id_proof"])
    missing = [doc for doc in required if doc not in uploaded_doc_types]

    if missing:
        return False, f"Missing required documents: {', '.join(missing)}"
    return True, "All required documents present"

def get_required_docs(claim_type: str) -> List[str]:
    """Get the list of required document types for a claim type."""
    return REQUIRED_DOCS.get(claim_type, ["id_proof"])


# ── Gate 3: Fraud Assessment (Production — Hard + Soft + ML + Image) ─
def run_fraud_assessment(
    claim: Claim,
    user: User,
    ocr_amount: Optional[float] = None,
    doc_count: int = 0,
    ocr_date: Optional[str] = None,
    provider_name: Optional[str] = None,
    uploaded_doc_types: Optional[List[str]] = None,
    is_duplicate_claim: bool = False,
    signature_stamp_failed: bool = False,
    duplicate_image_detected: bool = False,
) -> Dict:
    """
    Run the full production fraud assessment:
      1. Hard rules (instant rejection check)
      2. Soft rules (weighted score)
      3. ML model (fraud probability 0–1)
      4. Combined decision

    Returns complete fraud assessment result.
    """
    claim_type = claim.claim_type or "auto"
    required_docs = get_required_docs(claim_type)
    uploaded = uploaded_doc_types or []

    # ── 1. Hard Rules ────────────────────────────────────────────────
    hard_violated, hard_results = evaluate_hard_rules(
        claim_amount=claim.claim_amount,
        policy_limit=user.policy_limit or 10000.0,
        policy_end_str=user.policy_end,
        uploaded_doc_types=uploaded,
        required_doc_types=required_docs,
        is_duplicate=is_duplicate_claim,
        signature_stamp_failed=signature_stamp_failed,
    )

    # ── 2. Soft Rules ────────────────────────────────────────────────
    soft_score, soft_results = evaluate_soft_rules(
        claim_amount=claim.claim_amount,
        policy_limit=user.policy_limit or 10000.0,
        prior_claims=user.claim_count or 0,
        prior_fraud_flags=user.fraud_flags or 0,
        incident_date_str=claim.incident_date or datetime.utcnow().strftime("%Y-%m-%d"),
        submission_date=claim.submitted_at or datetime.utcnow(),
        policy_start_str=user.policy_start,
        ocr_amount=ocr_amount,
        ocr_date=ocr_date,
        provider_name=provider_name,
    )

    # ── 3. ML Model (probability 0–1) ────────────────────────────────
    ocr_mismatch = 0
    if ocr_amount is not None and claim.claim_amount > 0:
        if abs(ocr_amount - claim.claim_amount) > (claim.claim_amount * 0.15):
            ocr_mismatch = 1

    days_since = _days_since(claim.incident_date)
    late_reporting = 1 if days_since > 30 else 0

    is_weekend = 0
    try:
        inc_date = datetime.strptime(
            claim.incident_date or datetime.utcnow().strftime("%Y-%m-%d"), "%Y-%m-%d"
        ).date()
        is_weekend = 1 if inc_date.weekday() >= 5 else 0
    except Exception:
        pass

    ml_features = {
        "claim_amount": claim.claim_amount,
        "claim_to_limit_ratio": claim.claim_amount / max(user.policy_limit or 10000, 1),
        "prior_claims": user.claim_count or 0,
        "prior_fraud_flags": user.fraud_flags or 0,
        "days_since_incident": days_since,
        "policy_age_days": _days_since(user.policy_start),
        "is_round_number": int(claim.claim_amount % 100 == 0),
        "is_weekend": is_weekend,
        "document_count": doc_count,
        "ocr_mismatch": ocr_mismatch,
        "late_reporting": late_reporting,
    }

    ml_probability = get_ml_fraud_probability(ml_features)  # 0–1
    ml_score_100 = round(ml_probability * 100, 2) if ml_probability >= 0 else -1.0

    # ── 4. Legacy fraud score (for backward compat) ──────────────────
    # Convert soft score (higher=safer) to rule score (higher=riskier)
    rule_score = max(0, 100 - soft_score)
    final_fraud_score = get_final_fraud_score(rule_score, ml_score_100)
    verdict = get_fraud_verdict(final_fraud_score)

    # ── 5. Combined Decision ─────────────────────────────────────────
    combined = make_combined_decision(
        hard_rule_violated=hard_violated,
        soft_score=soft_score,
        ml_probability=ml_probability,
        duplicate_image=duplicate_image_detected,
    )

    # Build triggered rules list (for UI/audit)
    triggered_rules = []
    for hr in hard_results:
        if hr["triggered"]:
            triggered_rules.append({
                "rule_id": hr["rule_id"],
                "rule_name": hr["name"],
                "severity": "critical",
                "score_impact": 100.0,
                "description": hr["description"],
                "type": "hard",
            })
    for sr in soft_results:
        if sr["triggered"] and sr["points"] < 0:
            triggered_rules.append({
                "rule_id": sr["rule_id"],
                "rule_name": sr["rule_name"],
                "severity": sr["severity"],
                "score_impact": abs(sr["points"]),
                "description": sr["detail"],
                "type": "soft",
            })

    return {
        # Legacy fields (backward compat with pipeline_service)
        "fraud_score": final_fraud_score,
        "rule_score": rule_score,
        "ml_score": ml_score_100 if ml_score_100 >= 0 else None,
        "verdict": verdict,
        "triggered_rules": triggered_rules,
        "ml_features": ml_features,

        # New production fields
        "hard_rule_violated": hard_violated,
        "hard_rule_results": hard_results,
        "soft_score": soft_score,
        "soft_rule_results": soft_results,
        "ml_probability": ml_probability,
        "combined_decision": combined,
        "duplicate_image_detected": duplicate_image_detected,
    }


# ── Gate 4: Risk & Settlement Calculator ────────────────────────────
DEDUCTIBLE_RATES = {
    "auto":     0.10,   # 10% deductible
    "health":   0.05,   # 5% co-pay
    "travel":   0.08,
    "property": 0.12,
}

def calculate_settlement(claim: Claim, user: User, fraud_score: float) -> Dict:
    """
    Calculate approved settlement amount considering deductibles,
    policy limits, and risk adjustments.
    """
    deductible_rate = DEDUCTIBLE_RATES.get(claim.claim_type, 0.10)
    deductible      = round(claim.claim_amount * deductible_rate, 2)
    base_amount     = claim.claim_amount - deductible

    # Risk adjustment: reduce payout slightly for medium-risk claims
    risk_adjustment = 1.0
    if fraud_score >= 40:
        risk_adjustment = 0.90   # 10% reduction for medium risk
    elif fraud_score >= 20:
        risk_adjustment = 0.95

    approved = round(base_amount * risk_adjustment, 2)
    approved = min(approved, user.policy_limit or 10000.0)  # cap at policy limit

    risk_score = round((fraud_score * 0.6) + ((claim.claim_amount / (user.policy_limit or 10000)) * 40), 2)

    return {
        "claim_amount":     claim.claim_amount,
        "deductible":       deductible,
        "deductible_rate":  f"{int(deductible_rate*100)}%",
        "risk_adjustment":  f"{int(risk_adjustment*100)}%",
        "approved_amount":  approved,
        "risk_score":       min(risk_score, 100),
        "policy_limit":     user.policy_limit,
    }


# ── Gate 5: STP Decision ─────────────────────────────────────────────
def make_stp_decision(
    eligibility_ok: bool,
    docs_ok: bool,
    fraud_score: float,
    risk_score: float,
) -> Dict:
    """
    Final STP decision gate (legacy — kept for pipeline_service compat).
    Returns decision: auto_approved | manual_review | rejected
    """
    if not eligibility_ok:
        return {"decision": "rejected", "reason": "Failed eligibility check", "auto": True}

    if not docs_ok:
        return {"decision": "manual_review", "reason": "Missing documents — adjuster verification needed", "auto": False}

    if fraud_score >= settings.FRAUD_SCORE_THRESHOLD:
        return {"decision": "manual_review", "reason": f"High fraud score ({fraud_score:.1f}/100) — investigation required", "auto": False}

    if fraud_score <= settings.AUTO_APPROVE_SCORE and risk_score <= 40:
        return {"decision": "auto_approved", "reason": "All STP gates cleared — auto-approved", "auto": True}

    if fraud_score <= 50:
        return {"decision": "auto_approved", "reason": "Low-moderate risk — approved with standard review", "auto": True}

    return {"decision": "manual_review", "reason": "Moderate risk flags — adjuster confirmation required", "auto": False}


# ── Helpers ──────────────────────────────────────────────────────────
def _days_since(date_str: Optional[str]) -> int:
    if not date_str:
        return 365
    try:
        d = datetime.strptime(date_str, "%Y-%m-%d").date()
        return (datetime.utcnow().date() - d).days
    except Exception:
        return 365
