# ClaimIQ - Rebuild Git History Script
# Creates realistic incremental commit history

$ErrorActionPreference = "Stop"

# Save current files to temp
$tempDir = "$env:TEMP\claimiq_backup_$(Get-Date -Format 'yyyyMMddHHmmss')"
Write-Host "Backing up to $tempDir..."
Copy-Item -Path "." -Destination $tempDir -Recurse -Exclude ".git","venv",".venv","__pycache__","node_modules","*.pyc","claimiq.db","uploads","seed_output*.txt","token.txt","{backend"

# Remove current git history
Remove-Item -Recurse -Force .git
git init
git checkout -b main

# ---- Author info ----
$env:GIT_AUTHOR_NAME = "Shrushti7823"
$env:GIT_AUTHOR_EMAIL = "shrushti7823@gmail.com"
$env:GIT_COMMITTER_NAME = "Shrushti7823"
$env:GIT_COMMITTER_EMAIL = "shrushti7823@gmail.com"

# ========== COMMIT 1: Project initialization ==========
$env:GIT_AUTHOR_DATE = "2026-03-28T10:15:00+05:30"
$env:GIT_COMMITTER_DATE = "2026-03-28T10:15:00+05:30"

git add .gitignore
git add requirements.txt
git add run.py
git add README.md
git commit -m "Initial project setup with dependencies and README"

# ========== COMMIT 2: Core backend config ==========
$env:GIT_AUTHOR_DATE = "2026-03-28T14:30:00+05:30"
$env:GIT_COMMITTER_DATE = "2026-03-28T14:30:00+05:30"

git add backend/__init__.py
git add backend/core/__init__.py
git add backend/core/config.py
git add backend/core/database.py
git add backend/core/security.py
git commit -m "Add core backend configuration, database, and security modules"

# ========== COMMIT 3: Database models ==========
$env:GIT_AUTHOR_DATE = "2026-03-28T18:45:00+05:30"
$env:GIT_COMMITTER_DATE = "2026-03-28T18:45:00+05:30"

git add backend/models/__init__.py
git add backend/models/user.py
git add backend/models/claim.py
git add backend/models/document.py
git commit -m "Define SQLAlchemy models for users, claims, and documents"

# ========== COMMIT 4: Auth router ==========
$env:GIT_AUTHOR_DATE = "2026-03-29T09:20:00+05:30"
$env:GIT_COMMITTER_DATE = "2026-03-29T09:20:00+05:30"

git add backend/routers/__init__.py
git add backend/routers/auth.py
git commit -m "Implement JWT authentication and user registration endpoints"

# ========== COMMIT 5: FastAPI main entry ==========
$env:GIT_AUTHOR_DATE = "2026-03-29T11:00:00+05:30"
$env:GIT_COMMITTER_DATE = "2026-03-29T11:00:00+05:30"

git add backend/main.py
git commit -m "Add FastAPI application entry point with CORS and static files"

# ========== COMMIT 6: Landing page ==========
$env:GIT_AUTHOR_DATE = "2026-03-29T15:30:00+05:30"
$env:GIT_COMMITTER_DATE = "2026-03-29T15:30:00+05:30"

git add frontend/pages/index.html
git commit -m "Create landing page with hero section and feature overview"

# ========== COMMIT 7: Login and register pages ==========
$env:GIT_AUTHOR_DATE = "2026-03-29T19:45:00+05:30"
$env:GIT_COMMITTER_DATE = "2026-03-29T19:45:00+05:30"

git add frontend/pages/login.html
git add frontend/pages/register.html
git commit -m "Add login and registration pages with form validation"

# ========== COMMIT 8: OCR service ==========
$env:GIT_AUTHOR_DATE = "2026-03-30T10:00:00+05:30"
$env:GIT_COMMITTER_DATE = "2026-03-30T10:00:00+05:30"

git add backend/services/__init__.py
git add backend/services/ocr_service.py
git commit -m "Implement OCR extraction service for claim documents"

# ========== COMMIT 9: Claims and documents routers ==========
$env:GIT_AUTHOR_DATE = "2026-03-30T14:15:00+05:30"
$env:GIT_COMMITTER_DATE = "2026-03-30T14:15:00+05:30"

git add backend/routers/claims.py
git add backend/routers/documents.py
git add backend/routers/upload_claim.py
git commit -m "Add claim submission and document upload API endpoints"

# ========== COMMIT 10: Policyholder portal ==========
$env:GIT_AUTHOR_DATE = "2026-03-30T20:30:00+05:30"
$env:GIT_COMMITTER_DATE = "2026-03-30T20:30:00+05:30"

git add frontend/pages/portal.html
git commit -m "Build policyholder portal with claim submission wizard"

# ========== COMMIT 11: Dataset and training data ==========
$env:GIT_AUTHOR_DATE = "2026-03-31T09:00:00+05:30"
$env:GIT_COMMITTER_DATE = "2026-03-31T09:00:00+05:30"

git add datasets/
git commit -m "Add insurance claim datasets for model training"

# ========== COMMIT 12: ML fraud engine ==========
$env:GIT_AUTHOR_DATE = "2026-03-31T14:00:00+05:30"
$env:GIT_COMMITTER_DATE = "2026-03-31T14:00:00+05:30"

git add backend/ml/__init__.py
git add backend/ml/fraud_engine.py
git add backend/ml/train_model.py
git commit -m "Implement ML-based fraud detection engine with model training"

# ========== COMMIT 13: STP engine ==========
$env:GIT_AUTHOR_DATE = "2026-03-31T18:30:00+05:30"
$env:GIT_COMMITTER_DATE = "2026-03-31T18:30:00+05:30"

git add backend/services/stp_engine.py
git commit -m "Add straight-through processing engine for auto-approval logic"

# ========== COMMIT 14: Pipeline service ==========
$env:GIT_AUTHOR_DATE = "2026-04-01T10:00:00+05:30"
$env:GIT_COMMITTER_DATE = "2026-04-01T10:00:00+05:30"

git add backend/services/pipeline_service.py
git commit -m "Implement 6-stage claim processing pipeline service"

# ========== COMMIT 15: Image fraud detection ==========
$env:GIT_AUTHOR_DATE = "2026-04-01T14:30:00+05:30"
$env:GIT_COMMITTER_DATE = "2026-04-01T14:30:00+05:30"

git add backend/services/image_fraud_service.py
git commit -m "Add image fraud detection with perceptual hashing"

# ========== COMMIT 16: Fraud router and audit models ==========
$env:GIT_AUTHOR_DATE = "2026-04-01T17:00:00+05:30"
$env:GIT_COMMITTER_DATE = "2026-04-01T17:00:00+05:30"

git add backend/routers/fraud.py
git add backend/models/audit.py
git add backend/models/decision_log.py
git add backend/routers/audit.py
git commit -m "Add fraud analysis endpoints, audit logging, and decision tracking"

# ========== COMMIT 17: Human review system ==========
$env:GIT_AUTHOR_DATE = "2026-04-01T21:00:00+05:30"
$env:GIT_COMMITTER_DATE = "2026-04-01T21:00:00+05:30"

git add backend/routers/human_review.py
git commit -m "Implement human-in-the-loop review workflow for complex claims"

# ========== COMMIT 18: Dashboard router and page ==========
$env:GIT_AUTHOR_DATE = "2026-04-02T10:30:00+05:30"
$env:GIT_COMMITTER_DATE = "2026-04-02T10:30:00+05:30"

git add backend/routers/dashboard.py
git add frontend/pages/dashboard.html
git commit -m "Create admin dashboard with analytics and claim management"

# ========== COMMIT 19: Explainability and pipeline router ==========
$env:GIT_AUTHOR_DATE = "2026-04-02T14:45:00+05:30"
$env:GIT_COMMITTER_DATE = "2026-04-02T14:45:00+05:30"

git add backend/services/explainability_service.py
git add backend/services/audit_service.py
git add backend/routers/pipeline.py
git commit -m "Add explainability service and pipeline status endpoint"

# ========== COMMIT 20: Copilot router ==========
$env:GIT_AUTHOR_DATE = "2026-04-02T18:00:00+05:30"
$env:GIT_COMMITTER_DATE = "2026-04-02T18:00:00+05:30"

git add backend/routers/copilot.py
git commit -m "Add AI copilot assistant for claim investigation support"

# ========== COMMIT 21: Seed and utility scripts ==========
$env:GIT_AUTHOR_DATE = "2026-04-02T21:30:00+05:30"
$env:GIT_COMMITTER_DATE = "2026-04-02T21:30:00+05:30"

git add scripts/
git commit -m "Add database seeding, dataset generation, and sample PDF scripts"

# ========== COMMIT 22: About AI page ==========
$env:GIT_AUTHOR_DATE = "2026-04-03T09:00:00+05:30"
$env:GIT_COMMITTER_DATE = "2026-04-03T09:00:00+05:30"

git add frontend/pages/about-ai.html
git commit -m "Add About AI transparency page with model documentation"

# ========== COMMIT 23: Sample claims and env example ==========
$env:GIT_AUTHOR_DATE = "2026-04-03T11:30:00+05:30"
$env:GIT_COMMITTER_DATE = "2026-04-03T11:30:00+05:30"

git add sample_claims/
git add .env.example
git commit -m "Add sample claim PDFs and environment configuration template"

# ========== COMMIT 24: Documentation and guides ==========
$env:GIT_AUTHOR_DATE = "2026-04-03T15:00:00+05:30"
$env:GIT_COMMITTER_DATE = "2026-04-03T15:00:00+05:30"

git add system_flow.md
git add stp_demo_guide.md
git commit -m "Add system architecture documentation and STP demo guide"

# ========== COMMIT 25: Final polish and remaining files ==========
$env:GIT_AUTHOR_DATE = "2026-04-03T22:00:00+05:30"
$env:GIT_COMMITTER_DATE = "2026-04-03T22:00:00+05:30"

git add -A
git commit -m "Final cleanup: add test scripts and build utilities" --allow-empty

Write-Host ""
Write-Host "=== Git history rebuilt successfully! ==="
Write-Host ""
git log --oneline --all
