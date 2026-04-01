"""
ClaimIQ - Human Review Router (Human-in-the-Loop)
===================================================
Manages the human review workflow:
  - GET  /queue          → list claims pending human review
  - GET  /{claim_id}     → get full review context for a claim
  - POST /               → submit a review decision (approve/reject/request_docs)

Decisions are logged to DecisionLog for ML training feedback.
"""
from datetime import datetime
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from backend.core.database import get_db
from backend.core.security import get_current_admin
from backend.models.claim import Claim
from backend.models.user import User
from backend.models.document import Document, FraudAlert
from backend.models.decision_log import DecisionLog
from backend.services.audit_service import log_event

router = APIRouter()


# ── Schemas ──────────────────────────────────────────────────────────
class ReviewDecision(BaseModel):
    claim_id: int = Field(..., description="ID of the claim to review")
    decision: str = Field(..., description="approved | rejected | request_docs")
    reason: Optional[str] = Field(None, description="Explanation for the decision")
    requested_documents: Optional[List[str]] = Field(
        None, description="List of doc_types to request (only for request_docs)"
    )


class ReviewResponse(BaseModel):
    message: str
    claim_id: int
    decision: str
    claim_reference: str


# ── GET /queue — List claims pending human review ────────────────────
@router.get("/queue")
def get_review_queue(
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    """
    Get all claims currently in manual_review status.
    Returns claims ordered by fraud score (highest risk first).
    """
    claims = db.query(Claim).filter(
        Claim.status == "manual_review"
    ).order_by(
        Claim.fraud_score.desc()
    ).offset(skip).limit(limit).all()

    return {
        "total": db.query(Claim).filter(Claim.status == "manual_review").count(),
        "claims": [
            {
                "id": c.id,
                "claim_reference": c.claim_reference,
                "claim_type": c.claim_type,
                "claim_amount": c.claim_amount,
                "fraud_score": c.fraud_score,
                "risk_score": c.risk_score,
                "confidence_score": c.confidence_score,
                "soft_rule_score": c.soft_rule_score,
                "ml_fraud_probability": c.ml_fraud_probability,
                "hard_rule_violated": c.hard_rule_violated,
                "duplicate_image_detected": c.duplicate_image_detected,
                "documents_verified": c.documents_verified,
                "settlement_notes": c.settlement_notes,
                "approved_amount": c.approved_amount,
                "submitted_at": c.submitted_at,
                "policy_number": c.policy_number,
            }
            for c in claims
        ],
    }


# ── GET /{claim_id} — Full review context ───────────────────────────
@router.get("/{claim_id}")
def get_review_context(
    claim_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    """
    Get full context for reviewing a claim: claim details, documents,
    fraud analysis, OCR data, explainability report, and audit trail.
    """
    claim = db.query(Claim).filter(Claim.id == claim_id).first()
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")

    user = db.query(User).filter(User.id == claim.user_id).first()

    # Documents with OCR data
    documents = []
    for d in (claim.documents or []):
        documents.append({
            "id": d.id,
            "doc_type": d.doc_type,
            "file_name": d.file_name,
            "file_size_kb": d.file_size_kb,
            "ocr_confidence": d.ocr_confidence,
            "ocr_fields": d.ocr_fields,
            "is_verified": d.is_verified,
            "tamper_detected": d.tamper_detected,
            "has_signature": d.has_signature,
            "has_stamp": d.has_stamp,
            "detected_doc_type": d.detected_doc_type,
            "image_phash": d.image_phash,
        })

    # Fraud alerts
    fraud_alerts = [
        {
            "rule_id": a.rule_id,
            "rule_name": a.rule_name,
            "severity": a.severity,
            "description": a.description,
            "score_impact": a.score_impact,
        }
        for a in (claim.fraud_alerts or [])
    ]

    # Previous decisions on this claim
    prev_decisions = [
        {
            "decision": dl.decision,
            "reason": dl.reason,
            "reviewer": dl.reviewer_email,
            "created_at": dl.created_at.isoformat() if dl.created_at else None,
        }
        for dl in (claim.decision_logs or [])
    ]

    # Policyholder profile
    profile = None
    if user:
        profile = {
            "full_name": user.full_name,
            "email": user.email,
            "policy_number": user.policy_number,
            "policy_type": user.policy_type,
            "policy_limit": user.policy_limit,
            "policy_start": user.policy_start,
            "policy_end": user.policy_end,
            "claim_count": user.claim_count,
            "fraud_flags": user.fraud_flags,
            "risk_score": user.risk_score,
        }

    return {
        "claim": {
            "id": claim.id,
            "claim_reference": claim.claim_reference,
            "claim_type": claim.claim_type,
            "claim_amount": claim.claim_amount,
            "incident_date": claim.incident_date,
            "incident_description": claim.incident_description,
            "status": claim.status,
            "approved_amount": claim.approved_amount,
            "deductible": claim.deductible,
            "settlement_notes": claim.settlement_notes,
        },
        "scores": {
            "fraud_score": claim.fraud_score,
            "risk_score": claim.risk_score,
            "confidence_score": claim.confidence_score,
            "soft_rule_score": claim.soft_rule_score,
            "ml_fraud_probability": claim.ml_fraud_probability,
            "hard_rule_violated": claim.hard_rule_violated,
            "duplicate_image_detected": claim.duplicate_image_detected,
        },
        "documents": documents,
        "fraud_alerts": fraud_alerts,
        "explainability": claim.explainability_report,
        "policyholder": profile,
        "previous_decisions": prev_decisions,
    }


# ── POST / — Submit a review decision ───────────────────────────────
@router.post("/", response_model=ReviewResponse)
def submit_review(
    review: ReviewDecision,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    """
    Submit a human review decision. Updates the claim status and logs
    the decision for future ML training.

    Decisions:
      - approved   → claim proceeds to settlement
      - rejected   → claim is denied
      - request_docs → claim stays in review, policyholder notified
    """
    claim = db.query(Claim).filter(Claim.id == review.claim_id).first()
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")

    if claim.status not in ["manual_review", "submitted"]:
        raise HTTPException(
            status_code=400,
            detail=f"Claim is in '{claim.status}' state — cannot review"
        )

    valid_decisions = ["approved", "rejected", "request_docs"]
    if review.decision not in valid_decisions:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid decision. Must be one of: {valid_decisions}"
        )

    # Log the decision for ML training feedback
    decision_log = DecisionLog(
        claim_id=claim.id,
        reviewer_email=admin.email,
        decision=review.decision,
        reason=review.reason,
        requested_documents=review.requested_documents,
        original_ml_score=claim.ml_fraud_probability,
        original_rule_score=claim.fraud_score,
        original_soft_score=claim.soft_rule_score,
        original_hard_rule=claim.hard_rule_violated,
        final_outcome=review.decision if review.decision != "request_docs" else None,
    )
    db.add(decision_log)

    # Update claim based on decision
    if review.decision == "approved":
        claim.status = "approved"
        claim.payout_status = "processing"
        claim.settled_at = datetime.utcnow()
        claim.reviewed_by = admin.email
        claim.auto_decided = False
        claim.human_reviewer_notes = review.reason

    elif review.decision == "rejected":
        claim.status = "rejected"
        claim.payout_status = "rejected"
        claim.approved_amount = 0.0
        claim.reviewed_by = admin.email
        claim.auto_decided = False
        claim.human_reviewer_notes = review.reason

    elif review.decision == "request_docs":
        # Keep in manual_review but note what was requested
        claim.settlement_notes = (
            f"Additional documents requested: {', '.join(review.requested_documents or ['unspecified'])}. "
            f"Reviewer: {admin.email}. Reason: {review.reason or 'N/A'}"
        )
        claim.human_reviewer_notes = review.reason

    claim.current_stage = "completed" if review.decision != "request_docs" else "settlement"
    db.commit()

    # Audit log
    log_event(db, claim.id, "human_review",
              f"Human review: {review.decision.upper()} by {admin.email}", {
                  "decision": review.decision,
                  "reason": review.reason,
                  "reviewer": admin.email,
                  "requested_documents": review.requested_documents,
              }, actor=admin.email)

    return ReviewResponse(
        message=f"Review submitted: {review.decision}",
        claim_id=claim.id,
        decision=review.decision,
        claim_reference=claim.claim_reference,
    )
