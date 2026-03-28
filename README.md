# ClaimIQ — Enterprise Intelligent Insurance Claim Processing System

> AI-powered insurance claim processing with Explainable AI, 12-rule fraud detection, real-time pipeline tracking, and Google Gemini copilot.

---

## 🚀 Quick Start (5 Minutes)

### Prerequisites
- **Python 3.10+** installed
- **MySQL 8.0+** running (XAMPP / MySQL Server / WAMP)
- **Git** (optional)

### Step-by-Step Setup

```bash
# 1. Open terminal in project folder
cd c:\Users\Dell\OneDrive\Desktop\codes\claimiq1

# 2. Create virtual environment (skip if venv exists)
python -m venv venv

# 3. Activate virtual environment
venv\Scripts\activate

# 4. Install dependencies
pip install -r requirements.txt

# 5. Create MySQL database
python scripts/setup_mysql.py

# 6. Seed demo data (auto-runs on first start too)
python scripts/seed_db.py

# 7. Start the server
python run.py
```

### Access Points
| URL | Description |
|-----|-------------|
| http://localhost:8000 | Landing page |
| http://localhost:8000/login.html | Login page |
| http://localhost:8000/portal.html | Policyholder portal |
| http://localhost:8000/dashboard.html | Admin dashboard |
| http://localhost:8000/api/docs | Swagger API docs |

---

## 👤 Demo Accounts

| User | Email | Password | Scenario |
|------|-------|----------|----------|
| John Doe | john@demo.com | Demo@123 | ✅ Clean → Auto-Approved |
| Priya Sharma | priya@demo.com | Demo@123 | ✅ Health claim → Approved |
| Rahul Verma | rahul@demo.com | Demo@123 | ⚠️ Suspicious → Manual Review |
| Amit Kumar | amit@demo.com | Demo@123 | ❌ Fraud → Rejected |
| Admin | admin@claimiq.com | Admin@123 | 🛡️ Dashboard access |

---

## 📂 How to Submit Your Own Claim with Real Documents

### Step 1: Register or Login
- Go to http://localhost:8000/register.html
- Create an account with your policy details
- Or use a demo account

### Step 2: Submit a Claim
1. Click **Submit Claim** in the sidebar
2. Fill in:
   - **Claim Type**: Auto, Health, Travel, or Property
   - **Incident Date**: When the incident happened
   - **Claim Amount**: How much you're claiming
   - **Description**: Detailed description of the incident
3. Click **Continue to Documents**

### Step 3: Upload Your Documents
Upload real PDF/image documents like:
- Police reports
- Medical bills / invoices
- Photos of damage
- ID proof
- Booking confirmation

**Supported formats**: PDF, JPG, JPEG, PNG (max 10MB each)

The system will:
- Run **OCR** to extract text from your documents
- Extract **key fields** (amounts, dates, reference numbers)
- Detect potential **tampering**

### Step 4: Watch AI Pipeline Process
Click **Submit for AI Processing** and watch the 6-stage pipeline:
1. 📋 **Claim Submitted** — Queued for processing
2. 📄 **Document Verification** — OCR + completeness check
3. 🔍 **Fraud Analysis** — 12 rules + ML model scoring
4. 📊 **Risk Scoring** — Settlement calculation
5. ⚖️ **Decision Engine** — Auto-approve / manual review / reject
6. 💸 **Settlement** — Payout orchestration

### Step 5: View AI Explanation
Click on any claim to see the full **Explainable AI report**:
- Why the decision was made
- Which fraud rules triggered
- Risk breakdown (fraud, amount, behavioral)
- Confidence score
- Recommended action

---

## 🗄️ MySQL Database Schema

The database `claimiq` is created automatically. Tables:

| Table | Purpose |
|-------|---------|
| `users` | Policyholders, adjusters, admins |
| `claims` | All insurance claims with pipeline stages |
| `documents` | Uploaded documents with OCR results |
| `fraud_alerts` | Individual fraud rule violations |
| `audit_logs` | Full pipeline event audit trail |

### Manual MySQL Setup (if setup_mysql.py fails)
```sql
CREATE DATABASE IF NOT EXISTS claimiq CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

### MySQL Connection
Edit `.env` to match your MySQL credentials:
```
DATABASE_URL=mysql+pymysql://root:root@localhost:3306/claimiq
```
Change `root:root` to your MySQL username:password.

---

## 🧠 How the AI Works

### Fraud Detection (12 Rules)
| Rule | Severity | What it checks |
|------|----------|----------------|
| RULE_001 | High | Claim amount ≥90% of policy limit |
| RULE_002 | Critical | Multiple claims in 90 days |
| RULE_003 | Medium | Claim filed same day as incident |
| RULE_004 | Low | Weekend/holiday incident |
| RULE_005 | Medium | Round number claim amount |
| RULE_006 | High | Policy issued <30 days ago |
| RULE_007 | Critical | Prior fraud flags on record |
| RULE_008 | High | 3+ claims in 12 months |
| RULE_009 | High | Document amounts don't match claim |
| RULE_010 | Medium | Claim filed >30 days late |
| RULE_011 | Low | Unusual incident location |
| RULE_012 | High | OCR values contradict claim details |

### Decision Thresholds
- **Fraud Score 0-30**: Auto-approved (STP)
- **Fraud Score 31-60**: Standard review
- **Fraud Score 61-100**: Manual investigation required

### Settlement Calculation
```
Approved Amount = (Claim Amount - Deductible) × Risk Adjustment
```
Deductible rates: Auto 10%, Health 5%, Travel 8%, Property 12%

---

## 📡 API Endpoints

### Authentication
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/auth/register` | Register new user |
| POST | `/api/auth/login` | Login (returns JWT) |
| GET | `/api/auth/me` | Get current user |

### Claims
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/claims/submit` | Submit new claim |
| GET | `/api/claims/my` | Get user's claims |
| GET | `/api/claims/{id}/details` | Full claim details + AI report |
| GET | `/api/claims/admin/all` | Admin: all claims |
| PATCH | `/api/claims/admin/{id}/decide` | Admin: approve/reject |

### Documents
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/documents/upload/{claim_id}` | Upload document |
| GET | `/api/documents/claim/{claim_id}` | List documents |

### Pipeline & Dashboard
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/pipeline/{id}/status` | Real-time pipeline status |
| GET | `/api/dashboard/stats` | Admin KPIs |
| GET | `/api/dashboard/my-stats` | User stats |

### Copilot & Audit
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/copilot/chat` | AI chatbot |
| GET | `/api/audit/{claim_id}` | Claim audit trail |

---

## 🏗️ Project Structure

```
claimiq1/
├── backend/
│   ├── main.py              # FastAPI app entry point
│   ├── core/
│   │   ├── config.py        # Settings from .env
│   │   ├── database.py      # MySQL/SQLite connection
│   │   └── security.py      # JWT auth, password hashing
│   ├── models/
│   │   ├── user.py          # User model
│   │   ├── claim.py         # Claim model (pipeline stages)
│   │   ├── document.py      # Document + FraudAlert models
│   │   └── audit.py         # AuditLog model
│   ├── routers/
│   │   ├── auth.py          # Login/register endpoints
│   │   ├── claims.py        # Claim CRUD + admin
│   │   ├── documents.py     # File upload + OCR
│   │   ├── dashboard.py     # Analytics + KPIs
│   │   ├── pipeline.py      # Real-time status
│   │   ├── copilot.py       # Gemini AI chat
│   │   ├── fraud.py         # Fraud alerts
│   │   └── audit.py         # Audit logs
│   ├── services/
│   │   ├── pipeline_service.py    # 6-stage pipeline
│   │   ├── stp_engine.py         # STP processing gates
│   │   ├── explainability_service.py  # XAI reports
│   │   ├── audit_service.py      # Event logging
│   │   └── ocr_service.py        # Document OCR
│   └── ml/
│       ├── fraud_engine.py  # 12-rule fraud + ML
│       └── train_model.py   # Model training script
├── frontend/pages/
│   ├── index.html           # Landing page
│   ├── login.html           # Sign in
│   ├── register.html        # Sign up
│   ├── portal.html          # Policyholder portal
│   └── dashboard.html       # Admin dashboard
├── scripts/
│   ├── seed_db.py           # Demo data seeder
│   └── setup_mysql.py       # MySQL DB creation
├── .env                     # Configuration
├── requirements.txt         # Python dependencies
└── run.py                   # Quick start script
```

---

## 🔧 Troubleshooting

### "MySQL connection refused"
1. Make sure MySQL is running (XAMPP → Start MySQL)
2. Check username/password in `.env`
3. The system auto-falls back to SQLite if MySQL is unavailable

### "Module not found"
```bash
venv\Scripts\activate
pip install -r requirements.txt
```

### "Port 8000 already in use"
```bash
# Kill existing process
netstat -ano | findstr :8000
taskkill /PID <PID> /F
```

### "No claims showing"
Run the seed script:
```bash
python scripts/seed_db.py
```

---

## ⚙️ Tech Stack
- **Backend**: FastAPI + SQLAlchemy + Pydantic
- **Database**: MySQL (PyMySQL driver)
- **Frontend**: HTML + Tailwind CSS + Chart.js
- **AI/ML**: scikit-learn + Google Gemini API
- **Auth**: JWT (python-jose) + bcrypt
