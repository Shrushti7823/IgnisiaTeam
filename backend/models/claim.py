"""
ClaimIQ - Claim Model (Enhanced)
Now includes pipeline stage tracking and explainability report
"""
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Text, ForeignKey, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from backend.core.database import Base


class Claim(Base):
    __tablename__ = "claims"

    id                  = Column(Integer, primary_key=True, index=True)
    claim_reference     = Column(String(50), unique=True, index=True)

    # Claimant
    user_id             = Column(Integer, ForeignKey("users.id"), nullable=False)
    policy_number       = Column(String(100), index=True)

    # Claim details
    claim_type          = Column(String(50))
    incident_date       = Column(String(30))
    incident_description= Column(Text)
    claim_amount        = Column(Float, nullable=False)

    # Pipeline tracking
    current_stage       = Column(String(50), default="submitted")
    status              = Column(String(50), default="submitted")
    processing_type     = Column(String(20), default="STP")
    stp_eligible        = Column(Boolean, default=None)

    # AI scores
    fraud_score         = Column(Float, default=0.0)
    risk_score          = Column(Float, default=0.0)
    confidence_score    = Column(Float, default=0.0)

    # Settlement
    approved_amount     = Column(Float, default=0.0)
    deductible          = Column(Float, default=0.0)
    settlement_notes    = Column(Text)
    payout_status       = Column(String(30), default="pending")

    # Fraud flags (JSON list of rule violations)
    fraud_flags         = Column(JSON, default=list)

    # ── Production Rule Engine Results ────────────────
    hard_rule_violated  = Column(String(100), default=None)  # Which hard rule failed (NULL = none)
    soft_rule_score     = Column(Float, default=None)        # Weighted soft-rule score (0–100)
    ml_fraud_probability = Column(Float, default=None)       # ML model output (0–1)
    duplicate_image_detected = Column(Boolean, default=False)
    human_reviewer_notes = Column(Text, default=None)

    # Explainable AI report (JSON)
    explainability_report = Column(JSON, default=None)

    # Audit trail
    eligibility_passed  = Column(Boolean, default=None)
    documents_verified  = Column(Boolean, default=None)
    fraud_cleared       = Column(Boolean, default=None)
    auto_decided        = Column(Boolean, default=False)
    reviewed_by         = Column(String(100))

    # Pipeline stage timestamps
    submitted_at        = Column(DateTime(timezone=True), server_default=func.now())
    stage_doc_verified_at   = Column(DateTime(timezone=True))
    stage_fraud_analyzed_at = Column(DateTime(timezone=True))
    stage_risk_scored_at    = Column(DateTime(timezone=True))
    stage_decision_at       = Column(DateTime(timezone=True))
    stage_settled_at        = Column(DateTime(timezone=True))
    processed_at        = Column(DateTime(timezone=True))
    settled_at          = Column(DateTime(timezone=True))

    # Relationships
    user        = relationship("User", back_populates="claims")
    documents   = relationship("Document", back_populates="claim")
    fraud_alerts= relationship("FraudAlert", back_populates="claim")
    audit_logs  = relationship("AuditLog", back_populates="claim")
