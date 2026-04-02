"""
ClaimIQ Enterprise — Database Seed Script
Run: python scripts/seed_db.py
Creates demo users + 3 sample claim scenarios for showcase
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from datetime import datetime, timedelta
import random

from backend.core.database import engine, SessionLocal, Base
from backend.models.user import User
from backend.models.claim import Claim
from backend.models.document import FraudAlert
from backend.models.audit import AuditLog
from backend.core.security import get_password_hash
from backend.services.explainability_service import generate_explainability_report

# Create all tables
Base.metadata.create_all(bind=engine)

db = SessionLocal()

print("🌱 Seeding ClaimIQ Enterprise database...")

# ── Users ─────────────────────────────────────────────────────────────
users_data = [
    {
        "full_name": "ClaimIQ Admin",
        "email": "admin@claimiq.com",
        "password": "Admin@123",
        "role": "admin",
        "policy_number": "ADMIN-001",
        "policy_type": "auto",
        "policy_limit": 0,
    },
    {
        "full_name": "John Doe",
        "email": "john@demo.com",
        "password": "Demo@123",
        "role": "policyholder",
        "policy_number": "POL-JOHN-001",
        "policy_type": "auto",
        "policy_limit": 5000.0,
        "policy_start": "2023-01-01",
        "policy_end": "2027-12-31",
        "phone": "+91-9876543210",
    },
    {
        "full_name": "Priya Sharma",
        "email": "priya@demo.com",
        "password": "Demo@123",
        "role": "policyholder",
        "policy_number": "POL-PRIY-001",
        "policy_type": "health",
        "policy_limit": 10000.0,
        "policy_start": "2023-06-01",
        "policy_end": "2027-05-31",
    },
    {
        "full_name": "Rahul Verma",
        "email": "rahul@demo.com",
        "password": "Demo@123",
        "role": "policyholder",
        "policy_number": "POL-RAHU-001",
        "policy_type": "travel",
        "policy_limit": 3000.0,
        "policy_start": "2024-01-01",
        "policy_end": "2027-12-31",
        "fraud_flags": 1,
    },
    {
        "full_name": "Amit Kumar",
        "email": "amit@demo.com",
        "password": "Demo@123",
        "role": "policyholder",
        "policy_number": "POL-AMIT-001",
        "policy_type": "auto",
        "policy_limit": 5000.0,
        "policy_start": "2026-03-01",
        "policy_end": "2027-03-01",
        "fraud_flags": 2,
        "claim_count": 4,
    },
]

created_users = {}
for ud in users_data:
    existing = db.query(User).filter(User.email == ud["email"]).first()
    if not existing:
        user = User(
            full_name=ud["full_name"],
            email=ud["email"],
            hashed_password=get_password_hash(ud["password"]),
            role=ud.get("role", "policyholder"),
            policy_number=ud.get("policy_number"),
            policy_type=ud.get("policy_type"),
            policy_limit=ud.get("policy_limit", 10000),
            policy_start=ud.get("policy_start"),
            policy_end=ud.get("policy_end"),
            phone=ud.get("phone"),
            claim_count=ud.get("claim_count", 0),
            fraud_flags=ud.get("fraud_flags", 0),
            risk_score=0.0,
        )
        db.add(user)
        db.flush()
        created_users[ud["email"]] = user
        print(f"  ✅ User: {ud['email']}")
    else:
        created_users[ud["email"]] = existing
        print(f"  ⏭ User exists: {ud['email']}")

db.commit()

# ── 3 Demo Claim Scenarios ────────────────────────────────────────────
john = created_users.get("john@demo.com")
rahul = created_users.get("rahul@demo.com")
amit = created_users.get("amit@demo.com")
priya = created_users.get("priya@demo.com")

now = datetime.utcnow()

sample_claims = [
    # ── Scenario 1: CLEAN → Auto-Approved ──
    {
        "user": john,
        "claim_reference": "CLM-2026-10001",
        "claim_type": "auto",
        "incident_date": "2026-03-15",
        "incident_description": "Minor rear-end collision at MG Road signal. Vehicle front bumper damaged. Police report filed at Koregaon Park police station.",
        "claim_amount": 1200.0,
        "status": "approved",
        "current_stage": "completed",
        "fraud_score": 8.0,
        "risk_score": 15.0,
        "confidence_score": 92.0,
        "approved_amount": 1068.0,
        "deductible": 120.0,
        "payout_status": "paid",
        "auto_decided": True,
        "stp_eligible": True,
        "settlement_notes": "All STP gates cleared — auto-approved",
        "processed_at": now - timedelta(hours=2),
        "settled_at": now - timedelta(hours=2),
        "stage_doc_verified_at": now - timedelta(hours=2, minutes=8),
        "stage_fraud_analyzed_at": now - timedelta(hours=2, minutes=6),
        "stage_risk_scored_at": now - timedelta(hours=2, minutes=4),
        "stage_decision_at": now - timedelta(hours=2, minutes=2),
        "stage_settled_at": now - timedelta(hours=2),
        "scenario": "clean",
    },
    # ── Scenario 2: SUSPICIOUS → Manual Review ──
    {
        "user": rahul,
        "claim_reference": "CLM-2026-10002",
        "claim_type": "travel",
        "incident_date": "2026-03-25",
        "incident_description": "Flight cancellation — IndiGo 6E-456 cancelled due to weather. Requesting full refund of booking + hotel costs.",
        "claim_amount": 2800.0,
        "status": "manual_review",
        "current_stage": "completed",
        "fraud_score": 75.0,
        "risk_score": 65.0,
        "confidence_score": 72.5,
        "approved_amount": 2352.0,
        "deductible": 224.0,
        "payout_status": "pending",
        "auto_decided": False,
        "stp_eligible": False,
        "settlement_notes": "High fraud score (75/100) — investigation required",
        "processed_at": now - timedelta(hours=1),
        "stage_doc_verified_at": now - timedelta(hours=1, minutes=8),
        "stage_fraud_analyzed_at": now - timedelta(hours=1, minutes=6),
        "stage_risk_scored_at": now - timedelta(hours=1, minutes=4),
        "stage_decision_at": now - timedelta(hours=1, minutes=2),
        "stage_settled_at": now - timedelta(hours=1),
        "scenario": "suspicious",
    },
    # ── Scenario 3: FRAUD → Rejected ──
    {
        "user": amit,
        "claim_reference": "CLM-2026-10003",
        "claim_type": "auto",
        "incident_date": (now - timedelta(days=0)).strftime("%Y-%m-%d"),
        "incident_description": "Total vehicle damage in highway accident. Claiming full repair costs including engine replacement.",
        "claim_amount": 4900.0,
        "status": "rejected",
        "current_stage": "completed",
        "fraud_score": 95.0,
        "risk_score": 88.0,
        "confidence_score": 96.0,
        "approved_amount": 0.0,
        "deductible": 490.0,
        "payout_status": "rejected",
        "auto_decided": True,
        "stp_eligible": False,
        "settlement_notes": "Rejected — multiple critical fraud indicators detected",
        "processed_at": now - timedelta(minutes=30),
        "stage_doc_verified_at": now - timedelta(minutes=38),
        "stage_fraud_analyzed_at": now - timedelta(minutes=36),
        "stage_risk_scored_at": now - timedelta(minutes=34),
        "stage_decision_at": now - timedelta(minutes=32),
        "stage_settled_at": now - timedelta(minutes=30),
        "scenario": "fraud",
    },
    # ── Additional: Priya's clean health claim ──
    {
        "user": priya,
        "claim_reference": "CLM-2026-10004",
        "claim_type": "health",
        "incident_date": "2026-02-10",
        "incident_description": "Emergency appendix surgery at Apollo Hospital. 3-day hospitalization.",
        "claim_amount": 3500.0,
        "status": "approved",
        "current_stage": "completed",
        "fraud_score": 5.0,
        "risk_score": 10.0,
        "confidence_score": 95.0,
        "approved_amount": 3325.0,
        "deductible": 175.0,
        "payout_status": "paid",
        "auto_decided": True,
        "stp_eligible": True,
        "settlement_notes": "All STP gates cleared — auto-approved",
        "processed_at": now - timedelta(days=1),
        "settled_at": now - timedelta(days=1),
        "stage_doc_verified_at": now - timedelta(days=1, minutes=8),
        "stage_fraud_analyzed_at": now - timedelta(days=1, minutes=6),
        "stage_risk_scored_at": now - timedelta(days=1, minutes=4),
        "stage_decision_at": now - timedelta(days=1, minutes=2),
        "stage_settled_at": now - timedelta(days=1),
        "scenario": "clean",
    },
    # ── Additional: John's second claim ──
    {
        "user": john,
        "claim_reference": "CLM-2026-10005",
        "claim_type": "auto",
        "incident_date": "2026-03-28",
        "incident_description": "Windshield cracked by flying debris on Pune-Mumbai expressway.",
        "claim_amount": 600.0,
        "status": "approved",
        "current_stage": "completed",
        "fraud_score": 10.0,
        "risk_score": 12.0,
        "confidence_score": 90.0,
        "approved_amount": 540.0,
        "deductible": 60.0,
        "payout_status": "paid",
        "auto_decided": True,
        "stp_eligible": True,
        "settlement_notes": "Auto-approved via STP pipeline",
        "processed_at": now - timedelta(hours=5),
        "settled_at": now - timedelta(hours=5),
        "stage_doc_verified_at": now - timedelta(hours=5, minutes=8),
        "stage_fraud_analyzed_at": now - timedelta(hours=5, minutes=6),
        "stage_risk_scored_at": now - timedelta(hours=5, minutes=4),
        "stage_decision_at": now - timedelta(hours=5, minutes=2),
        "stage_settled_at": now - timedelta(hours=5),
        "scenario": "clean",
    },
]

# Fraud alerts for demo scenarios
fraud_alerts_data = {
    "CLM-2026-10002": [
        {"rule_id": "RULE_007", "rule_name": "Prior Fraud Flag on Account", "severity": "critical", "description": "Policyholder account has previous fraud flags on record", "score_impact": 30.0},
        {"rule_id": "RULE_001", "rule_name": "Claim Amount Near Policy Limit", "severity": "high", "description": "Claim amount is ≥90% of policy limit — unusual pattern", "score_impact": 20.0},
        {"rule_id": "RULE_005", "rule_name": "Round Number Claim Amount", "severity": "medium", "description": "Claim amount is a suspiciously round number", "score_impact": 8.0},
    ],
    "CLM-2026-10003": [
        {"rule_id": "RULE_001", "rule_name": "Claim Amount Near Policy Limit", "severity": "high", "description": "Claim amount ($4,900) is 98% of policy limit ($5,000)", "score_impact": 20.0},
        {"rule_id": "RULE_007", "rule_name": "Prior Fraud Flag on Account", "severity": "critical", "description": "Policyholder has 2 prior fraud flags on record", "score_impact": 30.0},
        {"rule_id": "RULE_003", "rule_name": "Claim Filed Same Day as Incident", "severity": "medium", "description": "Incident and claim submission on the same day — possibly pre-planned", "score_impact": 10.0},
        {"rule_id": "RULE_008", "rule_name": "High Claim Frequency", "severity": "high", "description": "Policyholder has 4+ claims in the last 12 months", "score_impact": 20.0},
        {"rule_id": "RULE_005", "rule_name": "Round Number Claim Amount", "severity": "medium", "description": "Claim amount $4,900 is a round number", "score_impact": 8.0},
        {"rule_id": "RULE_006", "rule_name": "Policy Newly Issued", "severity": "high", "description": "Policy was issued less than 30 days before the claim", "score_impact": 15.0},
    ],
}

for cd in sample_claims:
    existing = db.query(Claim).filter(Claim.claim_reference == cd["claim_reference"]).first()
    if not existing:
        # Generate explainability report
        triggered_rules = fraud_alerts_data.get(cd["claim_reference"], [])
        report = generate_explainability_report(
            claim_amount=cd["claim_amount"],
            policy_limit=cd["user"].policy_limit or 10000,
            fraud_score=cd["fraud_score"],
            risk_score=cd["risk_score"],
            confidence_score=cd["confidence_score"],
            decision=cd["status"],
            triggered_rules=triggered_rules,
            eligibility_passed=cd["stp_eligible"],
            docs_verified=True,
            settlement_notes=cd["settlement_notes"],
            approved_amount=cd["approved_amount"],
            deductible=cd["deductible"],
        )

        claim = Claim(
            claim_reference=cd["claim_reference"],
            user_id=cd["user"].id,
            policy_number=cd["user"].policy_number,
            claim_type=cd["claim_type"],
            incident_date=cd["incident_date"],
            incident_description=cd["incident_description"],
            claim_amount=cd["claim_amount"],
            status=cd["status"],
            current_stage=cd["current_stage"],
            fraud_score=cd["fraud_score"],
            risk_score=cd["risk_score"],
            confidence_score=cd["confidence_score"],
            approved_amount=cd["approved_amount"],
            deductible=cd["deductible"],
            payout_status=cd["payout_status"],
            auto_decided=cd["auto_decided"],
            stp_eligible=cd["stp_eligible"],
            settlement_notes=cd["settlement_notes"],
            eligibility_passed=cd.get("stp_eligible", True),
            documents_verified=True,
            fraud_cleared=cd["fraud_score"] < 70,
            fraud_flags=triggered_rules,
            explainability_report=report,
            processed_at=cd.get("processed_at"),
            settled_at=cd.get("settled_at"),
            stage_doc_verified_at=cd.get("stage_doc_verified_at"),
            stage_fraud_analyzed_at=cd.get("stage_fraud_analyzed_at"),
            stage_risk_scored_at=cd.get("stage_risk_scored_at"),
            stage_decision_at=cd.get("stage_decision_at"),
            stage_settled_at=cd.get("stage_settled_at"),
        )
        db.add(claim)
        db.flush()

        # Add fraud alerts
        for alert_data in triggered_rules:
            alert = FraudAlert(
                claim_id=claim.id,
                rule_id=alert_data["rule_id"],
                rule_name=alert_data["rule_name"],
                severity=alert_data["severity"],
                description=alert_data["description"],
                score_impact=alert_data["score_impact"],
            )
            db.add(alert)

        # Add audit trail entries
        stages = [
            ("submitted", "Claim submitted and queued for processing"),
            ("document_verification", "Document verification completed"),
            ("fraud_analysis", f"Fraud analysis complete — Score: {cd['fraud_score']:.1f}/100"),
            ("risk_scoring", f"Risk assessment: {cd['risk_score']:.1f}/100"),
            ("decision_engine", f"Decision: {cd['status'].upper()}"),
            ("settlement", f"Pipeline complete — Status: {cd['status'].upper()}"),
        ]
        for i, (stage, action) in enumerate(stages):
            audit_entry = AuditLog(
                claim_id=claim.id,
                stage=stage,
                action=action,
                details={"scenario": cd.get("scenario", ""), "step": i + 1},
                duration_ms=random.uniform(200, 1500),
                actor="system",
                created_at=cd.get("stage_doc_verified_at", now) + timedelta(minutes=i),
            )
            db.add(audit_entry)

        # Update user claim count
        cd["user"].claim_count = (cd["user"].claim_count or 0) + 1
        print(f"  ✅ Claim: {cd['claim_reference']} ({cd['status']}) — {cd['scenario'].upper()}")
    else:
        print(f"  ⏭ Claim exists: {cd['claim_reference']}")

db.commit()
db.close()

print("\n✅ Seed complete!")
print("─" * 50)
print("Demo Accounts:")
print("  👤 john@demo.com / Demo@123    (Clean claims)")
print("  👤 priya@demo.com / Demo@123   (Health claim)")
print("  👤 rahul@demo.com / Demo@123   (Suspicious → Manual Review)")
print("  👤 amit@demo.com / Demo@123    (Fraud → Rejected)")
print("  🛡️  admin@claimiq.com / Admin@123")
print("─" * 50)
print("Demo Scenarios:")
print("  ✅ CLM-2026-10001: Clean auto claim → Auto-Approved")
print("  ⚠️  CLM-2026-10002: Suspicious travel claim → Manual Review")
print("  ❌ CLM-2026-10003: Fraudulent claim → Rejected")
print("─" * 50)
print("Start server: python run.py")
print("API Docs:     http://localhost:8000/api/docs")
