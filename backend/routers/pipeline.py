"""
ClaimIQ - Pipeline Router
Real-time pipeline status tracking and audit trail
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.core.database import get_db
from backend.core.security import get_current_user
from backend.models.user import User
from backend.models.claim import Claim
from backend.services.pipeline_service import get_pipeline_status
from backend.services.audit_service import get_claim_audit_trail

router = APIRouter()


@router.get("/{claim_id}/status")
def pipeline_status(
    claim_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get real-time pipeline status for a claim (used for polling)."""
    claim = db.query(Claim).filter(Claim.id == claim_id).first()
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")
    if claim.user_id != current_user.id and current_user.role not in ["admin", "adjuster"]:
        raise HTTPException(status_code=403, detail="Access denied")

    status = get_pipeline_status(claim_id, db)
    if not status:
        raise HTTPException(status_code=404, detail="Pipeline status not found")
    return status


@router.get("/{claim_id}/audit")
def pipeline_audit(
    claim_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get full audit trail for a claim."""
    claim = db.query(Claim).filter(Claim.id == claim_id).first()
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")
    if claim.user_id != current_user.id and current_user.role not in ["admin", "adjuster"]:
        raise HTTPException(status_code=403, detail="Access denied")

    return {
        "claim_id": claim_id,
        "claim_reference": claim.claim_reference,
        "audit_trail": get_claim_audit_trail(db, claim_id),
    }
