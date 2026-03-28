"""
ClaimIQ - User Model
"""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Float
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from backend.core.database import Base


class User(Base):
    __tablename__ = "users"

    id              = Column(Integer, primary_key=True, index=True)
    full_name       = Column(String(255), nullable=False)
    email           = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    phone           = Column(String(20))
    role            = Column(String(20), default="policyholder")  # policyholder | adjuster | admin
    is_active       = Column(Boolean, default=True)

    # Policy info
    policy_number   = Column(String(100), unique=True, index=True)
    policy_type     = Column(String(50))   # auto | health | travel | property
    policy_limit    = Column(Float, default=10000.0)
    policy_start    = Column(String(20))
    policy_end      = Column(String(20))

    # Risk profile
    claim_count     = Column(Integer, default=0)
    fraud_flags     = Column(Integer, default=0)
    risk_score      = Column(Float, default=0.0)

    created_at      = Column(DateTime(timezone=True), server_default=func.now())
    updated_at      = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    claims          = relationship("Claim", back_populates="user")
