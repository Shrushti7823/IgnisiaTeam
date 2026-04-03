# ClaimIQ — STP System Demonstration Guide
## Convincing the Judge: This is a Straight-Through Processing (STP) Based System

---

## 🎯 What is STP (Straight-Through Processing)?

**Straight-Through Processing (STP)** is an automated end-to-end claim processing methodology where insurance claims flow through a series of validation gates **without manual intervention** — from submission to settlement. Only claims that fail automated checks are escalated to human reviewers.

### How ClaimIQ Implements STP

ClaimIQ implements a **5-Gate STP Pipeline** with a **6-Stage Processing Flow**:

```
Submission → Document Verification → Fraud Analysis → Risk Scoring → Decision Engine → Settlement
     ↓              ↓                      ↓               ↓              ↓               ↓
  Gate 1          Gate 2                Gate 3           Gate 4         Gate 5        Payout
 Eligibility    Doc Intel          Fraud (12 rules)    Risk/Coverage    STP/Manual    Auto-settle
```

| Gate | Name | What it Checks |
|------|------|---------------|
| **Gate 1** | Eligibility Filter | Policy active? Amount under STP limit ($5,000)? Claim type eligible? No prior fraud flags? |
| **Gate 2** | Document Intelligence | All required docs uploaded? OCR confidence adequate? Auto-detect document type? |
| **Gate 3** | Fraud Scoring | 6 hard rules (instant reject) + 6 soft rules (weighted score) + ML model (Random Forest) + Image fraud detection |
| **Gate 4** | Risk & Coverage | Deductible calculation, risk adjustment, policy limit cap, settlement amount |
| **Gate 5** | STP Decision | All gates passed → **Auto-Approve**. Any gate failed → **Manual Review** or **Auto-Reject** |

---

## 📋 Pre-Demo Checklist

Before starting the demonstration, ensure:

1. ✅ Backend server running (`python run.py`)
2. ✅ ML model trained (Admin Dashboard → ML Model → Retrain)
3. ✅ Database seeded with demo users
4. ✅ Sample PDFs generated (`python scripts/generate_sample_pdfs.py`)

### Demo Accounts

| Role | Email | Password | Policy | Use Case |
|------|-------|----------|--------|----------|
| **Clean User** | john@demo.com | Demo@123 | POL-2026-001, $10,000 limit | STP auto-approval |
| **Suspicious User** | amit@demo.com | Demo@123 | POL-2026-003, $5,000 limit, 2 fraud flags | Fraud rejection |
| **Manual Review** | rahul@demo.com | Demo@123 | POL-2026-002, prior fraud flag | Manual review escalation |
| **Admin** | admin@claimiq.com | Admin@123 | N/A | Full system visibility |

---

## ✅ DEMO 1: STP Auto-Approval (Clean Claim)

### Step-by-Step

1. **Login** as `john@demo.com / Demo@123`
2. Navigate to **Submit Claim**
3. Fill in:
   - **Claim Type**: Auto / Vehicle
   - **Incident Date**: 3 days ago
   - **Amount**: $1,200
   - **Description**: "Minor parking lot collision, front bumper and headlight damage"
4. Click **Continue to Documents**
5. Upload `sample_claims/sample_claim_approved.pdf` as **Invoice**
6. Click **Submit for AI Processing**

### What the Judge Will See

1. **Real-Time Pipeline Visualization**: Each of the 6 stages animates live
2. **Stage Detail Cards**: Shows what the AI is checking at each step
3. **Processing Log**: Timestamped entries for each operation
4. **Final Result**:
   - ✅ Fraud Score: ~8–15 out of 100 (LOW)
   - ✅ Confidence: ~85%+
   - ✅ Decision: **AUTO-APPROVED**
   - ✅ Approved Amount: ~$1,080 (after 10% auto deductible)

### Key Evidence Points

- **No human touched this claim** — fully automated
- **All 5 gates passed** — eligibility ✅, documents ✅, fraud clear ✅, risk OK ✅, STP ✅
- **Audit trail shows** every pipeline step with millisecond timestamps
- **AI Explanation** generated automatically explaining why it was approved
- **The system justifies its decision** with specific factors (low amount, clean history, valid docs)

---

## ❌ DEMO 2: Fraud Detection → Rejection (Suspicious Claim)

### Step-by-Step

1. **Login** as `amit@demo.com / Demo@123`
2. Navigate to **Submit Claim**
3. Fill in:
   - **Claim Type**: Health / Medical
   - **Incident Date**: 45 days ago (important — triggers late reporting rule!)
   - **Amount**: $4,800 (important — near policy limit!)
   - **Description**: "Severe back pain from workplace incident, required extensive treatment"
4. Click **Continue to Documents**
5. Upload `sample_claims/sample_claim_rejected.pdf` as **Medical Bill**
6. Click **Submit for AI Processing**

### What the Judge Will See

1. **Pipeline flags issues at multiple stages**
2. **Fraud Analysis Stage** — lights up RED, shows triggered rules:

| Rule | Severity | Description | Score Impact |
|------|----------|-------------|-------------|
| SOFT_HIGH_RATIO | High | Claim amount is ≥90% of policy limit | +20 |
| SOFT_PRIOR_FRAUD | Critical | Account has 2 prior fraud flags | +30 |
| SOFT_LATE_REPORT | Medium | Reported 45 days after incident (>30 days) | +15 |
| SOFT_ROUND_NUMBER | Low | Claim amount is a suspiciously round number | +5 |
| SOFT_CLAIM_FREQ | Medium | Multiple claims in short period | +10 |

3. **Final Result**:
   - 🚨 Fraud Score: ~75–95 out of 100 (CRITICAL)
   - ❌ Decision: **REJECTED** or **MANUAL_REVIEW**
   - Full AI explanation detailing every risk factor

### Key Evidence Points

- **System detected fraud without any human input**
- **Multiple independent rules corroborated** each other
- **ML model + rule engine agree** on high risk
- **Every triggered rule is explained** with plain-language descriptions
- **The system is conservative** — flags suspicious claims for human review rather than blindly rejecting

---

## 🔍 DEMO 3: Admin Dashboard — Full Transparency

### Step-by-Step

1. **Login** as `admin@claimiq.com / Admin@123`
2. Walk through each tab:

### Overview Tab
- **KPI cards**: Total claims, STP rate, fraud flagged, total payout
- **Charts**: Status distribution, claims by type, fraud score distribution
- **Recent claims table**: All claims with fraud scores at a glance

### All Claims Tab
- Filter by status: Approved, Rejected, Manual Review
- Click any claim for full AI report with explanation

### Fraud Alerts Tab
- Active rule violations across all claims
- Each alert shows: rule ID, severity, description, score impact
- Admin can resolve alerts after investigation

### Manual Review Queue Tab
- Claims flagged by AI for human decision
- Side-by-side view: AI recommendation vs claim details
- Admin can Approve or Reject with one click
- **This proves human-in-the-loop**: AI recommends, human decides for borderline cases

### Audit Logs Tab
- **Complete pipeline audit trail** — every action logged
- Timestamps, stages, durations, actors (system vs human)
- **Regulatory compliance**: full traceability of every decision

### ML Model Tab
- **Model performance metrics**: Accuracy, ROC-AUC, F1-Score, Precision, Recall
- **Feature importance chart**: Shows which factors the ML model weights highest
- **Confusion matrix**: Shows model's true positive/negative rates
- **Model retraining**: Admin can upload new data and retrain the model
- **This proves the system learns** — not static rules, but adaptive AI

---

## 🏛️ Arguments for the Judge: Why ClaimIQ is a Legitimate STP System

### 1. Fully Automated End-to-End Processing
> "The system processes claims from submission to settlement without any manual human intervention for low-risk claims. This is the core definition of Straight-Through Processing."

**Evidence**: Show Demo 1 — claim goes from submission to approval in under 5 minutes with zero human action.

### 2. Multi-Layer Fraud Detection
> "The system employs a defense-in-depth approach with 12 fraud rules, a machine learning model, and image fraud detection working in concert."

**Evidence**: Show Demo 2 — system catches multiple fraud indicators that a human reviewer might miss individually.

### 3. Explainable AI (XAI) — No Black Box
> "Every decision is fully explained. The system provides bullet-point summaries, risk factor breakdowns, confidence scores, and specific rule citations for every claim."

**Evidence**: Open any claim detail modal — show the AI Explanation section with factors and recommendations.

### 4. Human-in-the-Loop for Borderline Cases
> "The system doesn't blindly reject or approve. Claims with moderate risk scores are escalated to the Manual Review Queue where a human adjuster makes the final decision."

**Evidence**: Show the Manual Queue tab with pending claims and the approve/reject buttons.

### 5. Complete Audit Trail
> "Every pipeline stage, every rule evaluation, every decision is logged with millisecond precision. This provides full regulatory compliance and post-hoc auditability."

**Evidence**: Show Audit Logs tab and the per-claim audit trail in the claim detail modal.

### 6. Adaptive Machine Learning
> "The fraud detection model is not static. It is trained on real claim data and can be retrained as new patterns emerge, ensuring the system evolves with changing fraud tactics."

**Evidence**: Show ML Model tab with performance metrics, feature importance, and retraining capability.

### 7. Fair and Consistent Processing
> "Unlike human adjusters who may have unconscious biases, the STP system applies the same rules identically to every claim, ensuring fairness and consistency."

**Evidence**: Show same claim type/amount processed identically for different users (when risk profiles are similar).

### 8. Transparency to Policyholders
> "Policyholders can see their claim progress through the pipeline in real-time, view AI explanations, and understand why their claim was approved or rejected."

**Evidence**: Show the policyholder portal with pipeline visualization and AI explanation.

---

## 📊 Technical Architecture Summary

```
┌──────────────────────────────────────────────────────────────┐
│                    ClaimIQ Architecture                        │
├──────────────────────────────────────────────────────────────┤
│                                                               │
│  Frontend (HTML/Tailwind/Chart.js)                            │
│    ├── Policyholder Portal (portal.html)                      │
│    ├── Admin Dashboard (dashboard.html)                       │
│    ├── Landing Page (index.html)                              │
│    └── About AI (about-ai.html)                               │
│                                                               │
│  Backend (Python/FastAPI)                                     │
│    ├── Auth & Security (JWT tokens)                           │
│    ├── Claims API (CRUD + pipeline trigger)                   │
│    ├── Document Processing (OCR via pdfplumber/Pillow)        │
│    ├── STP Engine (5-gate pipeline)                           │
│    │    ├── Gate 1: Eligibility Filter                        │
│    │    ├── Gate 2: Document Intelligence                     │
│    │    ├── Gate 3: Fraud Engine                              │
│    │    │    ├── 6 Hard Rules (instant reject)                │
│    │    │    ├── 6 Soft Rules (weighted scoring)              │
│    │    │    ├── ML Model (Random Forest)                     │
│    │    │    └── Image Fraud (pHash/dHash)                    │
│    │    ├── Gate 4: Risk & Settlement Calculator              │
│    │    └── Gate 5: STP Decision Gate                         │
│    ├── Explainability Service (AI explanations)               │
│    ├── Audit Service (pipeline event logging)                 │
│    ├── Human Review API (approve/reject queue)                │
│    └── AI Copilot (Google Gemini integration)                 │
│                                                               │
│  Database (SQLite/MySQL)                                      │
│    ├── Users, Policies, Claims                                │
│    ├── Documents, OCR Results                                 │
│    ├── Fraud Alerts, Rules                                    │
│    └── Audit Events, Pipeline Stages                          │
│                                                               │
│  ML Pipeline                                                  │
│    ├── Training Data (CSV datasets)                           │
│    ├── Feature Engineering (11 features)                      │
│    ├── Model: Random Forest Classifier                        │
│    ├── SMOTE for class imbalance                              │
│    └── Real-time prediction API                               │
│                                                               │
└──────────────────────────────────────────────────────────────┘
```

---

## 🔑 12 Fraud Rules Reference

### Hard Rules (Instant Rejection)
| ID | Rule | Trigger Condition |
|----|------|------------------|
| HR-001 | Policy Limit Exceeded | Claim amount > policy limit |
| HR-002 | Policy Expired | Policy end date in past |
| HR-003 | Missing Required Docs | Required docs not uploaded |
| HR-004 | Duplicate Claim | Identical claim already exists |
| HR-005 | Signature/Stamp Missing | Document lacks signature or stamp |
| HR-006 | Document Tampered | Image hash detects manipulation |

### Soft Rules (Weighted Scoring)
| ID | Rule | Trigger | Points |
|----|------|---------|--------|
| SR-001 | High Amount Ratio | Claim ≥90% of policy limit | -20 |
| SR-002 | Prior Fraud | Account has fraud flags | -15 to -30 |
| SR-003 | Late Reporting | >30 days since incident | -10 to -15 |
| SR-004 | Round Numbers | Amount divisible by 100 | -5 |
| SR-005 | New Policy | Policy <90 days old | -10 |
| SR-006 | OCR Mismatch | Document amount ≠ claim amount (>15%) | -15 |

---

## 🏁 Demonstration Sequence for Maximum Impact

1. **Start with the Landing Page** — Show the system's professional presentation
2. **Demo 1: Clean Claim** — Prove STP works (auto-approval in <5 mins)
3. **Demo 2: Suspicious Claim** — Prove fraud detection works  
4. **Admin Dashboard Overview** — Show enterprise-grade analytics
5. **Fraud Alerts** — Show rule-triggered alerts
6. **Audit Logs** — Show complete traceability
7. **ML Model** — Show the adaptive learning capability
8. **Claim Detail Modal** — Show AI explanation for any claim
9. **About AI Page** — Show the system discloses its AI capabilities and limitations

**Total demo time: 15–20 minutes**

---

## 📝 Quick Command Reference

```bash
# Start the system
cd c:\Users\Dell\OneDrive\Desktop\codes\claimiq12
python run.py

# Generate sample PDFs
python scripts\generate_sample_pdfs.py

# Train ML model (if needed)
python -c "from backend.ml.train_model import train_model; train_model()"

# Seed database (if needed)
python scripts\_run_seed.py

# Open in browser
# Policyholder Portal: http://localhost:8000/pages/portal.html
# Admin Dashboard:     http://localhost:8000/pages/dashboard.html
# Landing Page:        http://localhost:8000/pages/index.html
```
