"""
ClaimIQ - Intelligent Insurance Claim Processing System (Enterprise Edition)
FastAPI Backend - Main Application Entry Point
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse
import uvicorn
import os

from backend.routers import claims, auth, documents, fraud, dashboard
from backend.routers import pipeline, copilot, audit
from backend.routers import upload_claim, human_review
from backend.core.database import engine, Base
from backend.core.config import settings

# Create all tables on startup
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="ClaimIQ API",
    description="Enterprise Intelligent Insurance Claim Processing System with Explainable AI",
    version="3.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)

# CORS - allow frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files (frontend)
frontend_path = os.path.join(os.path.dirname(__file__), "..", "frontend")
if os.path.exists(frontend_path):
    app.mount("/static", StaticFiles(directory=frontend_path), name="static")

# Mount assets (videos, images, etc.)
assets_path = os.path.join(frontend_path, "assets")
if os.path.exists(assets_path):
    app.mount("/assets", StaticFiles(directory=assets_path), name="assets")

# Include routers
app.include_router(auth.router,           prefix="/api/auth",           tags=["Authentication"])
app.include_router(claims.router,         prefix="/api/claims",         tags=["Claims"])
app.include_router(documents.router,      prefix="/api/documents",      tags=["Documents"])
app.include_router(fraud.router,          prefix="/api/fraud",          tags=["Fraud"])
app.include_router(dashboard.router,      prefix="/api/dashboard",      tags=["Dashboard"])
app.include_router(pipeline.router,       prefix="/api/pipeline",       tags=["Pipeline"])
app.include_router(copilot.router,        prefix="/api/copilot",        tags=["Copilot"])
app.include_router(audit.router,          prefix="/api/audit",          tags=["Audit"])
app.include_router(upload_claim.router,   prefix="/api/upload-claim",   tags=["Upload Claim"])
app.include_router(human_review.router,   prefix="/api/human-review",   tags=["Human Review"])


@app.on_event("startup")
async def startup_event():
    """Auto-seed database with demo data on first run."""
    from backend.core.database import get_new_session
    from backend.models.user import User
    db = get_new_session()
    try:
        user_count = db.query(User).count()
        if user_count == 0:
            print("\n  🌱 Empty database detected — running auto-seed...")
            db.close()
            # Run seed script
            import subprocess, sys
            subprocess.run(
                [sys.executable, "scripts/seed_db.py"],
                cwd=os.path.dirname(os.path.dirname(__file__)),
            )
            print("  ✅ Auto-seed complete!\n")
        else:
            print(f"  ℹ️  Database has {user_count} users — skipping seed")
            db.close()
    except Exception as e:
        print(f"  ⚠️  Auto-seed check failed: {e}")
        db.close()


@app.get("/", include_in_schema=False)
async def serve_frontend():
    return FileResponse(os.path.join(frontend_path, "pages", "index.html"))


# Serve frontend pages directly
@app.get("/{page}.html", include_in_schema=False)
async def serve_page(page: str):
    file_path = os.path.join(frontend_path, "pages", f"{page}.html")
    if os.path.exists(file_path):
        return FileResponse(file_path, headers={"Cache-Control": "no-cache, no-store, must-revalidate", "Pragma": "no-cache", "Expires": "0"})
    return FileResponse(os.path.join(frontend_path, "pages", "index.html"))


# ── Convenience API aliases ──────────────────────────────────────────
@app.get("/claim-status/{claim_id}", tags=["Claims"])
async def alias_claim_status(claim_id: int):
    """Alias: forwards to /api/claims/status/{claim_id}."""
    from fastapi import Depends
    from backend.core.database import get_db, get_new_session
    from backend.models.claim import Claim
    db = get_new_session()
    try:
        claim = db.query(Claim).filter(Claim.id == claim_id).first()
        if not claim:
            return {"error": "Claim not found"}
        return {
            "claim_id": claim.id, "claim_reference": claim.claim_reference,
            "status": claim.status, "current_stage": claim.current_stage,
            "fraud_score": claim.fraud_score, "risk_score": claim.risk_score,
            "confidence_score": claim.confidence_score,
            "approved_amount": claim.approved_amount, "payout_status": claim.payout_status,
        }
    finally:
        db.close()


@app.get("/fraud-score/{claim_id}", tags=["Fraud"])
async def alias_fraud_score(claim_id: int):
    """Alias: forwards to /api/fraud/score/{claim_id}."""
    from backend.core.database import get_new_session
    from backend.models.claim import Claim
    from backend.models.document import FraudAlert
    db = get_new_session()
    try:
        claim = db.query(Claim).filter(Claim.id == claim_id).first()
        if not claim:
            return {"error": "Claim not found"}
        alerts = [{"rule_id": a.rule_id, "rule_name": a.rule_name, "severity": a.severity,
                    "description": a.description, "score_impact": a.score_impact}
                   for a in (claim.fraud_alerts or [])]
        return {
            "claim_id": claim.id, "claim_reference": claim.claim_reference,
            "scores": {"fraud_score": claim.fraud_score, "risk_score": claim.risk_score,
                        "confidence_score": claim.confidence_score},
            "production_scores": {"hard_rule_violated": claim.hard_rule_violated,
                                   "soft_rule_score": claim.soft_rule_score,
                                   "ml_fraud_probability": claim.ml_fraud_probability},
            "image_fraud": {"duplicate_image_detected": claim.duplicate_image_detected},
            "triggered_alerts": alerts, "alerts_count": len(alerts),
            "decision": claim.status, "fraud_cleared": claim.fraud_cleared,
        }
    finally:
        db.close()


@app.get("/health")
async def health_check():
    return {"status": "healthy", "version": "3.0.0", "system": "ClaimIQ Enterprise"}


if __name__ == "__main__":
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
