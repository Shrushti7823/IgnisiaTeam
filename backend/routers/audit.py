"""
ClaimIQ - Audit Router
View audit logs for claims and system events
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.core.database import get_db
from backend.core.security import get_current_user, get_current_admin
from backend.models.user import User
from backend.services.audit_service import get_claim_audit_trail, get_recent_events

router = APIRouter()


@router.get("/{claim_id}")
def claim_audit(
    claim_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get full audit trail for a specific claim."""
    return {
        "claim_id": claim_id,
        "audit_trail": get_claim_audit_trail(db, claim_id),
    }


@router.get("/recent/events")
def recent_events(
    limit: int = 50,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    """Admin: Get recent audit events across all claims."""
    return {
        "events": get_recent_events(db, limit),
    }
