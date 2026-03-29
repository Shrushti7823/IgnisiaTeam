"""
ClaimIQ - Authentication Router
Register, login, profile management
"""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr
from typing import Optional

from backend.core.database import get_db
from backend.core.security import (
    verify_password, get_password_hash, create_access_token, get_current_user
)
from backend.models.user import User

router = APIRouter()


class UserRegister(BaseModel):
    full_name:    str
    email:        EmailStr
    password:     str
    phone:        Optional[str] = None
    policy_number:Optional[str] = None
    policy_type:  Optional[str] = "auto"
    policy_limit: Optional[float] = 10000.0
    policy_start: Optional[str] = None
    policy_end:   Optional[str] = None


class UserOut(BaseModel):
    id:            int
    full_name:     str
    email:         str
    role:          str
    policy_number: Optional[str]
    policy_type:   Optional[str]
    policy_limit:  Optional[float]
    claim_count:   Optional[int]
    risk_score:    Optional[float]

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str
    user: UserOut


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def register(payload: UserRegister, db: Session = Depends(get_db)):
    """Register a new policyholder."""
    import uuid

    if db.query(User).filter(User.email == payload.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")

    # Generate a unique policy number using UUID to avoid collisions
    policy_num = payload.policy_number or f"POL-{uuid.uuid4().hex[:8].upper()}"

    user = User(
        full_name=payload.full_name,
        email=payload.email,
        hashed_password=get_password_hash(payload.password),
        phone=payload.phone,
        policy_number=policy_num,
        policy_type=payload.policy_type or "auto",
        policy_limit=payload.policy_limit or 10000.0,
        policy_start=payload.policy_start,
        policy_end=payload.policy_end,
        role="policyholder",
        claim_count=0,
        fraud_flags=0,
        risk_score=0.0,
    )

    try:
        db.add(user)
        db.commit()
        db.refresh(user)
    except Exception as e:
        db.rollback()
        print(f"  ❌ Registration DB error: {e}")
        raise HTTPException(status_code=400, detail=f"Registration failed: {str(e)}")

    print(f"  ✅ New user registered: {user.email} | policy: {user.policy_number} | type: {user.policy_type}")
    return user


@router.post("/login", response_model=Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """Login with email + password, returns JWT token."""
    user = db.query(User).filter(User.email == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = create_access_token({"sub": user.email})
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": user,
    }


@router.get("/me", response_model=UserOut)
def me(current_user: User = Depends(get_current_user)):
    """Get current user profile."""
    return current_user


@router.post("/admin/seed")
def seed_admin(db: Session = Depends(get_db)):
    """Create a default admin user (run once for setup)."""
    if db.query(User).filter(User.email == "admin@claimiq.com").first():
        return {"message": "Admin already exists"}

    admin = User(
        full_name="ClaimIQ Admin",
        email="admin@claimiq.com",
        hashed_password=get_password_hash("Admin@123"),
        role="admin",
        policy_number="ADMIN-001",
        policy_limit=0,
        claim_count=0,
        fraud_flags=0,
        risk_score=0.0,
    )
    db.add(admin)

    # Demo policyholder
    demo = User(
        full_name="John Doe",
        email="john@demo.com",
        hashed_password=get_password_hash("Demo@123"),
        role="policyholder",
        policy_number="POL-JOHN-001",
        policy_type="auto",
        policy_limit=5000.0,
        policy_start="2023-01-01",
        policy_end="2025-12-31",
        phone="+91-9876543210",
        claim_count=0,
        fraud_flags=0,
        risk_score=0.0,
    )
    db.add(demo)
    db.commit()

    return {
        "message": "Seed complete",
        "admin": {"email": "admin@claimiq.com", "password": "Admin@123"},
        "demo_user": {"email": "john@demo.com", "password": "Demo@123"},
    }
