"""
ClaimIQ - Audit Service
Central logging for all pipeline events and admin actions
"""
from datetime import datetime
from typing import Optional, Dict
from sqlalchemy.orm import Session
from backend.models.audit import AuditLog


def log_event(
    db: Session,
    claim_id: int,
    stage: str,
    action: str,
    details: Optional[Dict] = None,
    duration_ms: float = 0,
    actor: str = "system",
) -> AuditLog:
    """Create an audit log entry for a pipeline event."""
    entry = AuditLog(
        claim_id=claim_id,
        stage=stage,
        action=action,
        details=details or {},
        duration_ms=round(duration_ms, 2),
        actor=actor,
        created_at=datetime.utcnow(),
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


def get_claim_audit_trail(db: Session, claim_id: int):
    """Get full audit trail for a claim, ordered chronologically."""
    logs = db.query(AuditLog).filter(
        AuditLog.claim_id == claim_id
    ).order_by(AuditLog.created_at.asc()).all()

    return [
        {
            "id": log.id,
            "stage": log.stage,
            "action": log.action,
            "details": log.details,
            "duration_ms": log.duration_ms,
            "actor": log.actor,
            "timestamp": log.created_at.isoformat() if log.created_at else None,
        }
        for log in logs
    ]


def get_recent_events(db: Session, limit: int = 50):
    """Get recent audit events across all claims."""
    logs = db.query(AuditLog).order_by(
        AuditLog.created_at.desc()
    ).limit(limit).all()

    return [
        {
            "id": log.id,
            "claim_id": log.claim_id,
            "stage": log.stage,
            "action": log.action,
            "details": log.details,
            "duration_ms": log.duration_ms,
            "actor": log.actor,
            "timestamp": log.created_at.isoformat() if log.created_at else None,
        }
        for log in logs
    ]
