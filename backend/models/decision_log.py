"""
ClaimIQ - DecisionLog Model
Records every human review decision to create a feedback loop for ML model retraining.
Each row captures the reviewer's action + the system's scores at decision time.
"""
from sqlalchemy import Column, Integer, String, Float, DateTime, Text, ForeignKey, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from backend.core.database import Base


class DecisionLog(Base):
    __tablename__ = "decision_logs"

    id                  = Column(Integer, primary_key=True, index=True)
    claim_id            = Column(Integer, ForeignKey("claims.id"), nullable=False)

    # Reviewer info
    reviewer_email      = Column(String(255), nullable=False)
    decision            = Column(String(30), nullable=False)   # approved | rejected | request_docs
    reason              = Column(Text)
    requested_documents = Column(JSON, default=None)           # list of doc_types if decision == request_docs

    # Snapshot of system scores at decision time (for ML training feedback)
    original_ml_score   = Column(Float, default=None)
    original_rule_score = Column(Float, default=None)
    original_soft_score = Column(Float, default=None)
    original_hard_rule  = Column(String(100), default=None)
    final_outcome       = Column(String(30), default=None)     # outcome after review: approved | rejected

    created_at          = Column(DateTime(timezone=True), server_default=func.now())

    # Relationship
    claim = relationship("Claim", backref="decision_logs")
