"""
ClaimIQ - Dashboard & Fraud Router
Analytics, KPIs, fraud alert management (Enhanced)
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func

from backend.core.database import get_db
from backend.core.security import get_current_user, get_current_admin
from backend.models.claim import Claim
from backend.models.user import User
from backend.models.document import FraudAlert
from backend.models.audit import AuditLog

router = APIRouter()
fraud_router = APIRouter()


@router.get("/stats")
def dashboard_stats(
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    """Admin dashboard KPIs — enhanced with processing time and more metrics."""
    total_claims    = db.query(Claim).count()
    approved        = db.query(Claim).filter(Claim.status == "approved").count()
    rejected        = db.query(Claim).filter(Claim.status == "rejected").count()
    manual_review   = db.query(Claim).filter(Claim.status == "manual_review").count()
    pending_approval = db.query(Claim).filter(Claim.status == "pending_admin_approval").count()
    pending         = db.query(Claim).filter(Claim.status.in_(["submitted", "document_verification", "fraud_analysis", "risk_scoring", "decision_engine"])).count()
    stp_approved    = db.query(Claim).filter(Claim.auto_decided == True, Claim.status == "approved").count()

    total_payout    = db.query(func.sum(Claim.approved_amount)).filter(Claim.status == "approved").scalar() or 0
    avg_fraud_score = db.query(func.avg(Claim.fraud_score)).scalar() or 0
    fraud_flagged   = db.query(Claim).filter(Claim.fraud_score >= 70).count()

    stp_rate = round((stp_approved / max(approved, 1)) * 100, 1)

    # Average processing time (in seconds)
    processed_claims = db.query(Claim).filter(
        Claim.processed_at.isnot(None),
        Claim.submitted_at.isnot(None),
    ).all()
    avg_processing_time = 0
    if processed_claims:
        total_seconds = sum(
            (c.processed_at - c.submitted_at).total_seconds()
            for c in processed_claims
            if c.processed_at and c.submitted_at
        )
        avg_processing_time = round(total_seconds / len(processed_claims), 1)

    # Claims by type
    by_type = {}
    for claim_type in ["auto", "health", "travel", "property"]:
        by_type[claim_type] = db.query(Claim).filter(Claim.claim_type == claim_type).count()

    # Fraud score distribution
    fraud_distribution = {
        "low": db.query(Claim).filter(Claim.fraud_score < 30).count(),
        "medium": db.query(Claim).filter(Claim.fraud_score >= 30, Claim.fraud_score < 60).count(),
        "high": db.query(Claim).filter(Claim.fraud_score >= 60, Claim.fraud_score < 80).count(),
        "critical": db.query(Claim).filter(Claim.fraud_score >= 80).count(),
    }

    # Active fraud alerts count
    active_alerts = db.query(FraudAlert).filter(FraudAlert.is_resolved == False).count()

    # Recent claims
    recent = db.query(Claim).order_by(Claim.submitted_at.desc()).limit(10).all()
    recent_list = [
        {
            "id": c.id,
            "claim_reference": c.claim_reference,
            "claim_type": c.claim_type,
            "claim_amount": c.claim_amount,
            "status": c.status,
            "current_stage": c.current_stage,
            "fraud_score": c.fraud_score,
            "risk_score": c.risk_score,
            "approved_amount": c.approved_amount,
            "submitted_at": c.submitted_at,
            "processed_at": c.processed_at,
        }
        for c in recent
    ]

    return {
        "overview": {
            "total_claims":    total_claims,
            "approved":        approved,
            "rejected":        rejected,
            "manual_review":   manual_review,
            "pending_admin_approval": pending_approval,
            "pending":         pending,
            "fraud_flagged":   fraud_flagged,
            "stp_rate":        stp_rate,
            "active_alerts":   active_alerts,
        },
        "financials": {
            "total_payout":        round(total_payout, 2),
            "avg_fraud_score":     round(avg_fraud_score, 2),
            "avg_processing_time": avg_processing_time,
        },
        "claims_by_type":      by_type,
        "fraud_distribution":  fraud_distribution,
        "recent_claims":       recent_list,
    }


@router.get("/model-stats")
def model_stats(
    admin: User = Depends(get_current_admin),
):
    """Admin: get ML model training metrics for the dashboard."""
    from backend.ml.fraud_engine import get_training_metrics, get_feature_importances, is_model_available
    
    metrics = get_training_metrics()
    importances = get_feature_importances()
    model_available = is_model_available()
    
    if not metrics:
        return {
            "model_available": model_available,
            "metrics": None,
            "feature_importance": None,
            "message": "No training metrics found. Train the model first.",
        }
    
    return {
        "model_available": model_available,
        "trained_at": metrics.get("trained_at"),
        "training_time_seconds": metrics.get("training_time_seconds"),
        "dataset_size": metrics.get("dataset_size"),
        "model_type": metrics.get("model_type"),
        "used_smote": metrics.get("used_smote"),
        "fraud_rate": metrics.get("fraud_rate"),
        "performance": metrics.get("performance"),
        "confusion_matrix": metrics.get("confusion_matrix"),
        "feature_importance": importances,
        "model_version": metrics.get("model_version"),
    }


@router.get("/my-stats")
def user_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Policyholder dashboard stats."""
    claims = db.query(Claim).filter(Claim.user_id == current_user.id).all()
    total = len(claims)
    approved = sum(1 for c in claims if c.status == "approved")
    pending  = sum(1 for c in claims if c.status in ["submitted", "eligibility_check", "document_review", "document_verification", "fraud_check", "fraud_analysis", "risk_assessment", "risk_scoring", "decision_engine", "manual_review", "pending_admin_approval"])
    rejected = sum(1 for c in claims if c.status == "rejected")
    total_approved_amount = sum(c.approved_amount for c in claims if c.status == "approved")

    return {
        "total_claims":         total,
        "approved_claims":      approved,
        "pending_claims":       pending,
        "rejected_claims":      rejected,
        "total_settled_amount": round(total_approved_amount, 2),
        "policy_number":        current_user.policy_number,
        "policy_type":          current_user.policy_type,
        "policy_limit":         current_user.policy_limit,
        "risk_score":           current_user.risk_score,
    }


# Fraud router
fraud_router = APIRouter()


@fraud_router.get("/alerts")
def fraud_alerts(
    resolved: bool = False,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    """Get all fraud alerts (admin only)."""
    alerts = db.query(FraudAlert).filter(FraudAlert.is_resolved == resolved)\
                .order_by(FraudAlert.created_at.desc()).limit(100).all()

    return [
        {
            "id": a.id,
            "claim_id": a.claim_id,
            "rule_id": a.rule_id,
            "rule_name": a.rule_name,
            "severity": a.severity,
            "description": a.description,
            "score_impact": a.score_impact,
            "is_resolved": a.is_resolved,
            "created_at": a.created_at,
        }
        for a in alerts
    ]


@fraud_router.patch("/alerts/{alert_id}/resolve")
def resolve_alert(
    alert_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    """Mark a fraud alert as resolved."""
    from datetime import datetime
    alert = db.query(FraudAlert).filter(FraudAlert.id == alert_id).first()
    if not alert:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Alert not found")

    alert.is_resolved = True
    alert.resolved_by = admin.email
    alert.resolved_at = datetime.utcnow()
    db.commit()
    return {"message": "Alert resolved", "alert_id": alert_id}
