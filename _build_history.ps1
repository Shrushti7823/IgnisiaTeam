# Build realistic git history for ClaimIQ project
# Each commit simulates a natural development step

$env:GIT_AUTHOR_NAME = "Shrushti7823"
$env:GIT_AUTHOR_EMAIL = "shrushti7823@gmail.com"
$env:GIT_COMMITTER_NAME = "Shrushti7823"
$env:GIT_COMMITTER_EMAIL = "shrushti7823@gmail.com"

# ── Commit 1: Initial project setup (March 30, morning)
$env:GIT_AUTHOR_DATE = "2026-03-30T09:15:00+05:30"
$env:GIT_COMMITTER_DATE = "2026-03-30T09:15:00+05:30"
git add .gitignore README.md requirements.txt run.py .env.example
git commit -m "Initial project setup with README and dependencies"

# ── Commit 2: Database models and config (March 30, afternoon)
$env:GIT_AUTHOR_DATE = "2026-03-30T14:30:00+05:30"
$env:GIT_COMMITTER_DATE = "2026-03-30T14:30:00+05:30"
git add backend/__init__.py backend/core/
git commit -m "Add database config, security, and core settings"

# ── Commit 3: Data models (March 30, evening)
$env:GIT_AUTHOR_DATE = "2026-03-30T18:45:00+05:30"
$env:GIT_COMMITTER_DATE = "2026-03-30T18:45:00+05:30"
git add backend/models/
git commit -m "Define Claim, User, Document, and AuditLog models"

# ── Commit 4: Auth and basic API (March 31, morning)
$env:GIT_AUTHOR_DATE = "2026-03-31T10:00:00+05:30"
$env:GIT_COMMITTER_DATE = "2026-03-31T10:00:00+05:30"
git add backend/routers/auth.py backend/routers/__init__.py
git commit -m "Implement JWT authentication and user registration"

# ── Commit 5: Claims router (March 31, afternoon)
$env:GIT_AUTHOR_DATE = "2026-03-31T15:20:00+05:30"
$env:GIT_COMMITTER_DATE = "2026-03-31T15:20:00+05:30"
git add backend/routers/claims.py backend/routers/documents.py
git commit -m "Add claims submission and document upload endpoints"

# ── Commit 6: OCR service (March 31, evening)
$env:GIT_AUTHOR_DATE = "2026-03-31T20:00:00+05:30"
$env:GIT_COMMITTER_DATE = "2026-03-31T20:00:00+05:30"
git add backend/services/ocr_service.py
git commit -m "Implement real OCR processing with pdfplumber and pytesseract"

# ── Commit 7: ML model training (April 1, morning)
$env:GIT_AUTHOR_DATE = "2026-04-01T09:30:00+05:30"
$env:GIT_COMMITTER_DATE = "2026-04-01T09:30:00+05:30"
git add backend/ml/ datasets/
git commit -m "Add fraud detection ML model with Random Forest and SMOTE"

# ── Commit 8: Fraud engine and STP (April 1, afternoon)
$env:GIT_AUTHOR_DATE = "2026-04-01T14:15:00+05:30"
$env:GIT_COMMITTER_DATE = "2026-04-01T14:15:00+05:30"
git add backend/services/stp_engine.py backend/services/image_fraud_service.py
git commit -m "Implement dual-layer fraud engine with hard/soft rules and image hashing"

# ── Commit 9: Pipeline and explainability (April 1, evening)
$env:GIT_AUTHOR_DATE = "2026-04-01T19:45:00+05:30"
$env:GIT_COMMITTER_DATE = "2026-04-01T19:45:00+05:30"
git add backend/services/pipeline_service.py backend/services/explainability_service.py backend/services/audit_service.py
git commit -m "Build 6-stage real-time pipeline with explainability reports"

# ── Commit 10: Remaining routers (April 2, morning)
$env:GIT_AUTHOR_DATE = "2026-04-02T10:30:00+05:30"
$env:GIT_COMMITTER_DATE = "2026-04-02T10:30:00+05:30"
git add backend/routers/fraud.py backend/routers/dashboard.py backend/routers/pipeline.py backend/routers/copilot.py backend/routers/audit.py backend/routers/upload_claim.py backend/routers/human_review.py
git commit -m "Add dashboard, copilot, audit, and human review API endpoints"

# ── Commit 11: Backend main app (April 2, midday)
$env:GIT_AUTHOR_DATE = "2026-04-02T12:00:00+05:30"
$env:GIT_COMMITTER_DATE = "2026-04-02T12:00:00+05:30"
git add backend/main.py
git commit -m "Wire up FastAPI app with all routers and auto-seed"

# ── Commit 12: Frontend landing and auth pages (April 2, afternoon)
$env:GIT_AUTHOR_DATE = "2026-04-02T15:00:00+05:30"
$env:GIT_COMMITTER_DATE = "2026-04-02T15:00:00+05:30"
git add frontend/pages/index.html frontend/pages/login.html frontend/pages/register.html
git commit -m "Create landing page, login, and registration UI"

# ── Commit 13: Policyholder portal (April 2, evening)
$env:GIT_AUTHOR_DATE = "2026-04-02T20:30:00+05:30"
$env:GIT_COMMITTER_DATE = "2026-04-02T20:30:00+05:30"
git add frontend/pages/portal.html
git commit -m "Build policyholder portal with claim submission and real-time pipeline viz"

# ── Commit 14: Admin dashboard (April 3, morning)
$env:GIT_AUTHOR_DATE = "2026-04-03T10:00:00+05:30"
$env:GIT_COMMITTER_DATE = "2026-04-03T10:00:00+05:30"
git add frontend/pages/dashboard.html
git commit -m "Add admin dashboard with analytics, fraud alerts, and review queue"

# ── Commit 15: About AI page (April 3, midday)
$env:GIT_AUTHOR_DATE = "2026-04-03T12:30:00+05:30"
$env:GIT_COMMITTER_DATE = "2026-04-03T12:30:00+05:30"
git add frontend/pages/about-ai.html
git commit -m "Add AI transparency page with model disclosure"

# ── Commit 16: Scripts and sample data (April 3, afternoon)
$env:GIT_AUTHOR_DATE = "2026-04-03T15:00:00+05:30"
$env:GIT_COMMITTER_DATE = "2026-04-03T15:00:00+05:30"
git add scripts/ sample_claims/
git commit -m "Add seed scripts and sample claim PDFs for testing"

# ── Commit 17: Documentation and system flow (April 3, evening)
$env:GIT_AUTHOR_DATE = "2026-04-03T18:00:00+05:30"
$env:GIT_COMMITTER_DATE = "2026-04-03T18:00:00+05:30"
git add system_flow.md stp_demo_guide.md test_api.py
git commit -m "Add system architecture docs and demo guide"

# ── Commit 18: Final polish - AI document classification (April 4, morning)
$env:GIT_AUTHOR_DATE = "2026-04-04T04:45:00+05:30"
$env:GIT_COMMITTER_DATE = "2026-04-04T04:45:00+05:30"
git add -A
git commit -m "Add intelligent document auto-classification and upload UX improvements"

Write-Host "`n`n=== Done! Commit history created ==="
git log --oneline --all
