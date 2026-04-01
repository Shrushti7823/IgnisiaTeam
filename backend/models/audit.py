"""
ClaimIQ - AuditLog Model
Tracks every pipeline step, manual actions, and system events
"""
from sqlalchemy import Column, Integer, String, Float, DateTime, Text, ForeignKey, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from backend.core.database import Base


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id          = Column(Integer, primary_key=True, index=True)
    claim_id    = Column(Integer, ForeignKey("claims.id"), nullable=False)

    stage       = Column(String(50))       # e.g. submitted, doc_verification, fraud_analysis
    action      = Column(String(200))      # e.g. "Eligibility check passed"
    details     = Column(JSON, default=dict)  # Structured data about this event
    duration_ms = Column(Float, default=0)    # Time taken for this step
    actor       = Column(String(100), default="system")  # system | admin email | user email

    created_at  = Column(DateTime(timezone=True), server_default=func.now())

    # Relationship
    claim = relationship("Claim", back_populates="audit_logs")
