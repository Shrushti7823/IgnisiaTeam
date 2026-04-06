#  ClaimIQ — Intelligent Insurance Claim Processing System
## Team Members 

This project was developed by the following team members:

- **Shrushti Handge**  
- **Shravani Hire**  
- **Shweta Gaidhani**  
- **Gargi Bagul**

> AI-Powered · Straight-Through Processing · Fraud Detection · Zero Human Intervention




### Prerequisites
- Python 3.10+
- pip
- A browser (Chrome/Firefox)

### Step 1 — Clone & Setup

```bash
# Navigate to the project folder
cd claimiq

# Create virtual environment
python -m venv venv

# Activate (Mac/Linux)
source venv/bin/activate
# OR Windows:
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Step 2 — Configure Environment

```bash
cp .env.example .env
# Edit .env if needed (SQLite works out of the box — no config needed)
```

### Step 3 — Train ML Fraud Model

```bash
python -m backend.ml.train_model
# Output: backend/ml/models/fraud_model.pkl
# Takes ~10 seconds on any modern CPU
```

### Step 4 — Seed Database

```bash
python scripts/seed_db.py
# Creates demo users + 5 sample claims
```

### Step 5 — Start Server

```bash
python run.py
# OR:
uvicorn backend.main:app --reload --port 8000
```

### Step 6 — Open Frontend

Open your browser and go to:
```
frontend/pages/index.html   ← Landing page
frontend/pages/login.html   ← Login
frontend/pages/portal.html  ← Policyholder portal
frontend/pages/dashboard.html ← Admin dashboard
```

OR open the index.html directly in browser (double-click the file).

---

##  Demo Credentials

| Role | Email | Password |
|------|-------|----------|
| 👤 Policyholder | john@demo.com | Demo@123 |
| 👤 Policyholder | priya@demo.com | Demo@123 |
| 🛡️ Admin | admin@claimiq.com | Admin@123 |

---

##  Project Structure

```
claimiq/
├── backend/
│   ├── main.py               ← FastAPI app entry point
│   ├── core/
│   │   ├── config.py         ← Settings (DB URL, thresholds)
│   │   ├── database.py       ← SQLAlchemy engine + session
│   │   └── security.py       ← JWT auth + password hashing
│   ├── models/
│   │   ├── user.py           ← User DB model
│   │   ├── claim.py          ← Claim DB model
│   │   └── document.py       ← Document + FraudAlert models
│   ├── routers/
│   │   ├── auth.py           ← Register, login, profile
│   │   ├── claims.py         ← Submit, track, approve claims
│   │   ├── documents.py      ← File upload + OCR
│   │   ├── dashboard.py      ← Admin analytics + user stats
│   │   └── fraud.py          ← Fraud alert management
│   ├── services/
│   │   ├── stp_engine.py     ← 5-gate STP pipeline
│   │   └── ocr_service.py    ← Document OCR + field extraction
│   └── ml/
│       ├── fraud_engine.py   ← 12-rule + ML fraud scorer
│       ├── train_model.py    ← Random Forest training script
│       └── models/           ← Trained model saved here
├── frontend/
│   └── pages/
│       ├── index.html        ← Landing page
│       ├── login.html        ← Login
│       ├── register.html     ← Registration
│       ├── portal.html       ← Policyholder portal
│       └── dashboard.html    ← Admin dashboard
├── scripts/
│   └── seed_db.py            ← Demo data seeder
├── datasets/
│   └── DATASET_REFERENCES.md ← Kaggle & open dataset links
├── uploads/                  ← Uploaded claim documents (auto-created)
├── run.py                    ← Easy start script
├── requirements.txt
└── .env.example
```

---

##  API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /api/auth/register | Register new user |
| POST | /api/auth/login | Login (returns JWT) |
| GET | /api/auth/me | Get current user |
| POST | /api/auth/admin/seed | Create demo accounts |
| POST | /api/claims/submit | Submit a claim |
| GET | /api/claims/my | Get my claims |
| GET | /api/claims/{id} | Get claim by ID |
| GET | /api/claims/{id}/details | Full claim details + fraud |
| GET | /api/claims/admin/all | Admin: all claims |
| PATCH | /api/claims/admin/{id}/decide | Admin: approve/reject |
| POST | /api/documents/upload/{claim_id} | Upload document |
| GET | /api/documents/claim/{claim_id} | List claim documents |
| GET | /api/dashboard/stats | Admin KPIs |
| GET | /api/dashboard/my-stats | User stats |
| GET | /api/fraud/alerts | Fraud alerts (admin) |
| PATCH | /api/fraud/alerts/{id}/resolve | Resolve fraud alert |

📖 **Full Swagger Docs**: http://localhost:8000/api/docs

---

##  AI/ML Components

### 1. Fraud Detection Engine (`backend/ml/fraud_engine.py`)
- **12 Rule-Based Rules**: Each fires if specific condition met (e.g., round amount, new policy, prior flags)
- **Random Forest ML Model**: Trained on 5,000 synthetic insurance samples
- **Blended Score**: `final = 60% rule_score + 40% ML_score`
- **Verdict**: 🟢 Clean → 🟡 Low Risk → 🟠 Medium → 🔴 High Risk

### 2. OCR Document Service (`backend/services/ocr_service.py`)
- **pdfplumber**: Extracts text from PDF claims (no OCR needed for digital docs)
- **pytesseract**: For scanned image documents (requires Tesseract installed)
- **Fallback**: Realistic mock OCR for demo without dependencies
- **Field Extraction**: Regex patterns to extract amount, date, reference number

### 3. STP Engine (`backend/services/stp_engine.py`)
5 automated gates:
1. Eligibility → Policy check, amount threshold
2. Documents → Required doc type check
3. Fraud → Score calculation
4. Settlement → Deductible + risk adjustment
5. Decision → Auto-approve, manual, or reject

---

## Database

**Default**: SQLite (`claimiq.db`) — zero setup, works immediately

**Production**: PostgreSQL
```bash
# Install PostgreSQL driver
pip install psycopg2-binary

# Update .env
DATABASE_URL=postgresql://user:pass@localhost:5432/claimiq
```

---

##  Enabling Real OCR

```bash
# 1. Install Python packages
pip install pdfplumber Pillow pytesseract

# 2. Install Tesseract on your OS
# Ubuntu: sudo apt install tesseract-ocr
# Mac:    brew install tesseract
# Windows: https://github.com/UB-Mannheim/tesseract/wiki

# 3. Uncomment in requirements.txt:
# pdfplumber==0.11.0
# Pillow==10.3.0
# pytesseract==0.3.10
```

---

##  Hackathon Demo Flow

**Recommended 3-minute demo script:**

1. **Open Landing Page** → Show stats (95% automation, <5 min, 12 rules)
2. **Admin Dashboard** → Show KPI cards + charts (use seeded data)
3. **Login as Policyholder** (john@demo.com / Demo@123)
4. **Submit a New Claim** → Type: auto, Amount: $1200, fill description
5. **Watch STP Pipeline** → 5 gates animate in real time
6. **See Result** → Auto-approved with fraud score + settlement amount
7. **Open ClaimIQ Copilot** → Show AI chat assistant
8. **Switch to Admin** → Show fraud alerts, manual review queue
9. **Approve manual claim** → Click Approve button

---

##  Troubleshooting

| Issue | Fix |
|-------|-----|
| `ModuleNotFoundError` | Run from project root, activate venv |
| `Connection refused` | Start backend first: `python run.py` |
| Admin endpoints return 403 | Login with admin@claimiq.com |
| Blank charts | Seed database first: `python scripts/seed_db.py` |
| Port 8000 in use | `uvicorn backend.main:app --port 8001` |

---

##  Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | HTML5 + TailwindCSS CDN + Chart.js |
| Backend | FastAPI (Python 3.10+) |
| Database | SQLite (dev) / PostgreSQL (prod) |
| ORM | SQLAlchemy 2.0 |
| Auth | JWT (python-jose) + bcrypt |
| ML | scikit-learn RandomForest |
| OCR | pdfplumber + pytesseract (optional) |
| Server | Uvicorn (ASGI) |

---

Built for 24-Hour Hackathon 2024 | ClaimIQ — Smart Claims, Instant Settlements ⚡
