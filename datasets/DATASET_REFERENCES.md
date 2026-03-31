# ClaimIQ — Dataset & Reference Links
# Use these datasets for model training, testing, and enrichment

## 🗃️ FRAUD DETECTION DATASETS
---

### 1. Insurance Fraud Detection Dataset (Kaggle)
URL: https://www.kaggle.com/datasets/buntyshah/auto-insurance-claims-data
- Auto insurance claims with fraud labels
- Fields: policy_number, incident_type, claim_amount, fraud_reported
- Size: ~15,000 rows | Format: CSV
- USE FOR: Training the Random Forest fraud model

### 2. Health Insurance Cross Sell (Kaggle)
URL: https://www.kaggle.com/datasets/anmolkumar/health-insurance-cross-sell-prediction
- Customer demographics + insurance vehicle data
- USE FOR: Policyholder risk profiling

### 3. Medical Insurance Cost Dataset (Kaggle)
URL: https://www.kaggle.com/datasets/mirichoi0218/insurance
- Age, BMI, region, charges (health claims)
- Fields: age, sex, bmi, children, smoker, region, charges
- USE FOR: Health claim amount estimation / settlement model

### 4. Fraud Detection (IEEE-CIS)
URL: https://www.kaggle.com/c/ieee-fraud-detection
- Large transaction fraud dataset (590K rows)
- USE FOR: Advanced fraud pattern learning

### 5. Vehicle Insurance Fraud (Kaggle)
URL: https://www.kaggle.com/datasets/shivamb/vehicle-claim-fraud-detection
- 15,000+ vehicle claims with fraud labels
- USE FOR: Direct training for auto claim fraud model

---

## 📄 OCR TESTING DOCUMENTS
---

### Sample Insurance Documents (for OCR testing):
- Fake/sample FIR reports: Generate via https://fakedetail.com/
- Medical bill samples: https://www.vertex42.com/ExcelTemplates/medical-bill.html
- Invoice templates: https://invoice-generator.com/

---

## 🧠 MODEL REFERENCES
---

### Scikit-learn Random Forest Docs:
URL: https://scikit-learn.org/stable/modules/generated/sklearn.ensemble.RandomForestClassifier.html

### Imbalanced Learn (for class imbalance in fraud):
URL: https://imbalanced-learn.org/stable/
Install: pip install imbalanced-learn
Usage: Use SMOTE to oversample fraud cases before training

### pdfplumber (PDF OCR):
URL: https://github.com/jsvine/pdfplumber
Docs: https://pdfplumber.readthedocs.io/

### EasyOCR (Image OCR):
URL: https://github.com/JaidedAI/EasyOCR
Install: pip install easyocr
Note: Downloads ~100MB model on first run

### Tesseract OCR:
URL: https://tesseract-ocr.github.io/
Install (Ubuntu): sudo apt install tesseract-ocr
Install (Mac): brew install tesseract
Python: pip install pytesseract

---

## 🗄️ DATABASE RESOURCES
---

### SQLite (default, no setup needed):
URL: https://www.sqlite.org/
Browser: https://sqlitebrowser.org/ (GUI tool to inspect DB)

### PostgreSQL (production):
URL: https://www.postgresql.org/
Docker: docker run --name claimiq-pg -e POSTGRES_PASSWORD=claimiq123 -p 5432:5432 -d postgres
Connection: postgresql://postgres:claimiq123@localhost:5432/claimiq

---

## 🌐 API TESTING TOOLS
---

### Swagger UI (built-in):
URL: http://localhost:8000/api/docs

### Postman Collection:
Import base URL: http://localhost:8000
Auth: Bearer token from /api/auth/login

### HTTPie (CLI testing):
Install: pip install httpie
Test: http POST localhost:8000/api/auth/login username=admin@claimiq.com password=Admin@123

---

## 📚 HACKATHON PRESENTATION REFERENCES
---

### Insurance Industry Stats:
- Global Insurance Fraud: https://www.insurancefraud.org/fraud-stats/
- STP in Insurance: https://www.mckinsey.com/industries/financial-services/our-insights
- Claim Processing Costs: ~$30-50/manual claim (Accenture 2023)

### Tech Stack Docs:
- FastAPI: https://fastapi.tiangolo.com/
- TailwindCSS: https://tailwindcss.com/docs
- SQLAlchemy: https://docs.sqlalchemy.org/
- Chart.js: https://www.chartjs.org/docs/
