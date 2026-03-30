"""
ClaimIQ - Claims Router
Full claim lifecycle: submit → process → approve/reject
Enhanced with pipeline service and explainability
"""
import random
import string
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from backend.core.database import get_db, get_new_session
from backend.core.security import get_current_user, get_current_admin
from backend.models.claim import Claim
from backend.models.user import User
from backend.models.document import FraudAlert
from backend.services.pipeline_service import run_pipeline_sync
from backend.services.audit_service import log_event

router = APIRouter()


# ── Schemas ──────────────────────────────────────────────────────────
class ClaimSubmit(BaseModel):
    claim_type:           str = Field(..., example="auto")
    incident_date:        str = Field(..., example="2024-01-15")
    incident_description: str = Field(..., example="Minor rear-end collision at traffic signal")
    claim_amount:         float = Field(..., gt=0, example=1500.00)


class ClaimOut(BaseModel):
    id: int
    claim_reference: str
    claim_type: str
    claim_amount: float
    status: str
    current_stage: Optional[str] = None
    fraud_score: float
    risk_score: float
    confidence_score: Optional[float] = 0
    approved_amount: float
    payout_status: str
    stp_eligible: Optional[bool]
    submitted_at: Optional[datetime]

    class Config:
        from_attributes = True


# ── Helpers ──────────────────────────────────────────────────────────
def _generate_reference() -> str:
    suffix = ''.join(random.choices(string.digits, k=5))
    return f"CLM-{datetime.utcnow().year}-{suffix}"


def _run_stp_pipeline_bg(claim_id: int):
    """Background task: runs full pipeline using its own DB session."""
    db = get_new_session()
    try:
        run_pipeline_sync(claim_id, db)
    except Exception as e:
        print(f"[Pipeline] Error processing claim {claim_id}: {e}")
    finally:
        db.close()


# ── Endpoints ────────────────────────────────────────────────────────
@router.post("/submit", response_model=ClaimOut, status_code=status.HTTP_201_CREATED)
def submit_claim(
    payload: ClaimSubmit,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Submit a new insurance claim. Pipeline runs in background."""
    claim = Claim(
        claim_reference=_generate_reference(),
        user_id=current_user.id,
        policy_number=current_user.policy_number,
        claim_type=payload.claim_type,
        incident_date=payload.incident_date,
        incident_description=payload.incident_description,
        claim_amount=payload.claim_amount,
        status="submitted",
        current_stage="submitted",
    )
    db.add(claim)
    db.commit()
    db.refresh(claim)

    # Kick off pipeline asynchronously with its own session
    background_tasks.add_task(_run_stp_pipeline_bg, claim.id)

    return claim


@router.get("/my", response_model=List[ClaimOut])
def my_claims(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get all claims for the logged-in policyholder."""
    return db.query(Claim).filter(Claim.user_id == current_user.id).order_by(Claim.submitted_at.desc()).all()


@router.get("/{claim_id}", response_model=ClaimOut)
def get_claim(
    claim_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a single claim by ID."""
    claim = db.query(Claim).filter(Claim.id == claim_id).first()
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")
    if claim.user_id != current_user.id and current_user.role not in ["admin", "adjuster"]:
        raise HTTPException(status_code=403, detail="Access denied")
    return claim


@router.get("/{claim_id}/details")
def get_claim_details(
    claim_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Full claim details including explainability, fraud analysis, documents, and audit trail."""
    claim = db.query(Claim).filter(Claim.id == claim_id).first()
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")

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

    documents = [
        {
            "doc_type": d.doc_type,
            "file_name": d.file_name,
            "is_verified": d.is_verified,
            "tamper_detected": d.tamper_detected,
            "ocr_confidence": d.ocr_confidence,
            "extracted_amount": d.ocr_fields.get("amount") if d.ocr_fields else None,
        }
        for d in (claim.documents or [])
    ]

    audit_trail = [
        {
            "stage": a.stage,
            "action": a.action,
            "duration_ms": a.duration_ms,
            "timestamp": a.created_at.isoformat() if a.created_at else None,
        }
        for a in (claim.audit_logs or [])
    ]

    return {
        "claim": {
            "id": claim.id,
            "claim_reference": claim.claim_reference,
            "claim_type": claim.claim_type,
            "claim_amount": claim.claim_amount,
            "approved_amount": claim.approved_amount,
            "deductible": claim.deductible,
            "status": claim.status,
            "current_stage": claim.current_stage,
            "processing_type": claim.processing_type,
            "stp_eligible": claim.stp_eligible,
            "auto_decided": claim.auto_decided,
            "payout_status": claim.payout_status,
            "incident_date": claim.incident_date,
            "incident_description": claim.incident_description,
            "settlement_notes": claim.settlement_notes,
            "confidence_score": claim.confidence_score,
            "submitted_at": claim.submitted_at,
            "processed_at": claim.processed_at,
            "settled_at": claim.settled_at,
        },
        "fraud_analysis": {
            "fraud_score": claim.fraud_score,
            "risk_score": claim.risk_score,
            "fraud_cleared": claim.fraud_cleared,
            "triggered_rules": fraud_alerts,
        },
        "explainability": claim.explainability_report,
        "pipeline": {
            "current_stage": claim.current_stage,
            "eligibility_passed": claim.eligibility_passed,
            "documents_verified": claim.documents_verified,
            "fraud_cleared": claim.fraud_cleared,
            "stages": {
                "submitted": claim.submitted_at.isoformat() if claim.submitted_at else None,
                "document_verification": claim.stage_doc_verified_at.isoformat() if claim.stage_doc_verified_at else None,
                "fraud_analysis": claim.stage_fraud_analyzed_at.isoformat() if claim.stage_fraud_analyzed_at else None,
                "risk_scoring": claim.stage_risk_scored_at.isoformat() if claim.stage_risk_scored_at else None,
                "decision_engine": claim.stage_decision_at.isoformat() if claim.stage_decision_at else None,
                "settlement": claim.stage_settled_at.isoformat() if claim.stage_settled_at else None,
            },
        },
        "documents": documents,
        "audit_trail": audit_trail,
    }


# ── Admin-only endpoints ─────────────────────────────────────────────
@router.get("/admin/all", response_model=List[ClaimOut])
def all_claims(
    status_filter: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    """Admin: get all claims with optional status filter."""
    q = db.query(Claim)
    if status_filter:
        q = q.filter(Claim.status == status_filter)
    return q.order_by(Claim.submitted_at.desc()).offset(skip).limit(limit).all()


@router.patch("/admin/{claim_id}/decide")
def admin_decide(
    claim_id: int,
    decision: str,
    notes: Optional[str] = None,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    """Admin: manually approve or reject a claim in manual_review."""
    claim = db.query(Claim).filter(Claim.id == claim_id).first()
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")
    if claim.status not in ["manual_review", "submitted"]:
        raise HTTPException(status_code=400, detail=f"Claim is already in '{claim.status}' state")

    claim.status = decision
    claim.reviewed_by = admin.email
    claim.auto_decided = False
    claim.settlement_notes = notes or claim.settlement_notes
    claim.current_stage = "completed"
    if decision == "approved":
        claim.payout_status = "processing"
        claim.settled_at = datetime.utcnow()
    else:
        claim.payout_status = "rejected"
        claim.approved_amount = 0.0

    db.commit()

    # Log admin action
    log_event(db, claim.id, "admin_decision",
              f"Admin {decision} claim", {
                  "decision": decision,
                  "admin": admin.email,
                  "notes": notes,
              }, actor=admin.email)

    return {"message": f"Claim {claim.claim_reference} {decision}", "claim_id": claim_id}


# ── GET /status/{claim_id} — Claim status (pipeline alias) ──────────
@router.get("/status/{claim_id}")
def claim_status(
    claim_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get current claim status including production scoring fields.
    Alias for quick status checks without full pipeline detail.
    """
    claim = db.query(Claim).filter(Claim.id == claim_id).first()
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")
    if claim.user_id != current_user.id and current_user.role not in ["admin", "adjuster"]:
        raise HTTPException(status_code=403, detail="Access denied")

    return {
        "claim_id": claim.id,
        "claim_reference": claim.claim_reference,
        "status": claim.status,
        "current_stage": claim.current_stage,
        "is_complete": claim.current_stage == "completed",
        "fraud_score": claim.fraud_score,
        "risk_score": claim.risk_score,
        "confidence_score": claim.confidence_score,
        "approved_amount": claim.approved_amount,
        "payout_status": claim.payout_status,
        "hard_rule_violated": claim.hard_rule_violated,
        "soft_rule_score": claim.soft_rule_score,
        "ml_fraud_probability": claim.ml_fraud_probability,
        "duplicate_image_detected": claim.duplicate_image_detected,
        "submitted_at": claim.submitted_at,
        "processed_at": claim.processed_at,
    }

