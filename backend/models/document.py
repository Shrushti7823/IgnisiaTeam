"""
ClaimIQ - Document & FraudAlert Models
"""
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Text, ForeignKey, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from backend.core.database import Base


class Document(Base):
    __tablename__ = "documents"

    id              = Column(Integer, primary_key=True, index=True)
    claim_id        = Column(Integer, ForeignKey("claims.id"), nullable=False)

    doc_type        = Column(String(100))   # police_report | medical_bill | invoice | photos | id_proof
    file_name       = Column(String(255))
    file_path       = Column(String(500))
    file_size_kb    = Column(Float)
    mime_type       = Column(String(100))

    # OCR Results
    ocr_text        = Column(Text)
    ocr_fields      = Column(JSON)         # extracted key-value pairs
    ocr_confidence  = Column(Float)

    # Verification
    is_verified     = Column(Boolean, default=False)
    verification_notes = Column(Text)
    tamper_detected = Column(Boolean, default=False)

    # ── Image Fraud Detection ────────────────────────
    image_phash     = Column(String(64), default=None)   # Perceptual hash
    image_dhash     = Column(String(64), default=None)   # Difference hash
    detected_doc_type = Column(String(50), default=None) # Auto-detected: medical_claim | vehicle_claim | property_claim
    has_signature   = Column(Boolean, default=None)
    has_stamp       = Column(Boolean, default=None)

    uploaded_at     = Column(DateTime(timezone=True), server_default=func.now())

    # Relationship
    claim = relationship("Claim", back_populates="documents")


class FraudAlert(Base):
    __tablename__ = "fraud_alerts"

    id          = Column(Integer, primary_key=True, index=True)
    claim_id    = Column(Integer, ForeignKey("claims.id"), nullable=False)

    rule_id     = Column(String(50))       # e.g. RULE_001
    rule_name   = Column(String(200))
    severity    = Column(String(20))       # low | medium | high | critical
    description = Column(Text)
    score_impact= Column(Float)            # how much this added to fraud score

    is_resolved = Column(Boolean, default=False)
    resolved_by = Column(String(100))
    resolved_at = Column(DateTime(timezone=True))

    created_at  = Column(DateTime(timezone=True), server_default=func.now())

    # Relationship
    claim = relationship("Claim", back_populates="fraud_alerts")
