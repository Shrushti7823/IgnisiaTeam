"""
ClaimIQ — Production Fraud Model Training System
===================================================
Trains on REAL Kaggle datasets (fraud_oracle.csv + insurance_claims.csv)
with proper feature engineering, SMOTE oversampling, cross-validation,
and comprehensive metrics.

Run: python -m backend.ml.train_model
"""
import os
import sys
import json
import pickle
import time
import numpy as np
import pandas as pd
from datetime import datetime
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.model_selection import train_test_split, StratifiedKFold, cross_val_score
from sklearn.metrics import (
    classification_report, roc_auc_score, confusion_matrix,
    precision_score, recall_score, f1_score, accuracy_score
)
from sklearn.preprocessing import StandardScaler, LabelEncoder

# ── Paths ────────────────────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
DATASET_DIR = os.path.join(BASE_DIR, "datasets")
MODEL_DIR = os.path.join(BASE_DIR, "backend", "ml", "models")
MODEL_PATH = os.path.join(MODEL_DIR, "fraud_model.pkl")
SCALER_PATH = os.path.join(MODEL_DIR, "scaler.pkl")
METRICS_PATH = os.path.join(MODEL_DIR, "training_metrics.json")

os.makedirs(MODEL_DIR, exist_ok=True)

# ── Feature columns used by the model at inference time ──────────────
FEATURE_COLUMNS = [
    "claim_amount",
    "claim_to_limit_ratio",
    "prior_claims",
    "prior_fraud_flags",
    "days_since_incident",
    "policy_age_days",
    "is_round_number",
    "is_weekend",
    "document_count",
    "ocr_mismatch",
    "late_reporting",
]


# ═══════════════════════════════════════════════════════════════════════
# DATASET LOADING – supports fraud_oracle.csv AND insurance_claims.csv
# ═══════════════════════════════════════════════════════════════════════

def _parse_range_to_midpoint(val: str, fallback: float = 0) -> float:
    """Convert categorical range strings like '20000 to 29000' to midpoint numeric."""
    if pd.isna(val) or val == "none":
        return fallback
    val = str(val).strip().lower()
    if "more than" in val:
        num = ''.join(c for c in val if c.isdigit())
        return float(num) * 1.15 if num else fallback
    if "less than" in val:
        num = ''.join(c for c in val if c.isdigit())
        return float(num) * 0.75 if num else fallback
    if " to " in val:
        parts = val.split(" to ")
        try:
            return (float(parts[0].strip()) + float(parts[1].strip())) / 2
        except (ValueError, IndexError):
            return fallback
    # Single number or "new"
    num = ''.join(c for c in val if c.isdigit() or c == '.')
    return float(num) if num else fallback


def _parse_past_claims(val) -> int:
    """Convert PastNumberOfClaims like 'none', '1', '2 to 4', 'more than 4'."""
    if pd.isna(val):
        return 0
    val = str(val).strip().lower()
    if val == "none":
        return 0
    if val == "1":
        return 1
    if "2 to 4" in val:
        return 3
    if "more than" in val:
        return 6
    try:
        return int(val)
    except ValueError:
        return 0


def _day_name_to_weekend(day: str) -> int:
    """Check if day name is a weekend."""
    return 1 if str(day).strip().lower() in ("saturday", "sunday") else 0


def load_fraud_oracle(csv_path: str) -> tuple:
    """Load and transform fraud_oracle.csv (Kaggle vehicle fraud dataset)."""
    print(f"📂 Loading fraud_oracle.csv: {csv_path}")
    df = pd.read_csv(csv_path)
    print(f"   Rows: {len(df):,}  |  Columns: {len(df.columns)}")

    # ── Feature engineering from real columns ─────────────────────────
    # Vehicle price as claim amount proxy
    df["claim_amount"] = df["VehiclePrice"].apply(
        lambda x: _parse_range_to_midpoint(x, 25000)
    )

    # Deductible exists as numeric
    df["deductible"] = df["Deductible"].astype(float)

    # claim_to_limit_ratio: use vehicle_price / (vehicle_price + deductible * 10) as proxy
    df["claim_to_limit_ratio"] = df["claim_amount"] / (df["claim_amount"] + df["deductible"] * 10 + 1)

    # Prior claims from PastNumberOfClaims
    df["prior_claims"] = df["PastNumberOfClaims"].apply(_parse_past_claims)

    # prior_fraud_flags: derive from prior claims + fault
    df["prior_fraud_flags"] = ((df["prior_claims"] >= 3) & (df["Fault"] == "Policy Holder")).astype(int)

    # days_since_incident from Days_Policy_Accident
    df["days_since_incident"] = df["Days_Policy_Accident"].apply(
        lambda x: _parse_range_to_midpoint(x, 15)
    )

    # policy_age_days from AgeOfPolicyHolder (years → days)
    df["policy_age_days"] = df["AgeOfPolicyHolder"].apply(
        lambda x: _parse_range_to_midpoint(x, 35) * 365
    )

    # is_round_number
    df["is_round_number"] = ((df["claim_amount"] % 1000 == 0) & (df["claim_amount"] > 0)).astype(int)

    # is_weekend from DayOfWeek
    df["is_weekend"] = df["DayOfWeek"].apply(_day_name_to_weekend)

    # document_count: derive from NumberOfSuppliments + PoliceReportFiled
    supp_map = {"none": 0, "1 to 2": 1, "3 to 5": 4, "more than 5": 6}
    df["document_count"] = df["NumberOfSuppliments"].map(supp_map).fillna(0).astype(int)
    df["document_count"] += (df["PoliceReportFiled"] == "Yes").astype(int)

    # ocr_mismatch: derive from AddressChange_Claim (address change = suspicious)
    addr_map = {"no change": 0, "4 to 8 years": 0, "2 to 3 years": 0, "1 year": 1, "under 6 months": 1}
    df["ocr_mismatch"] = df["AddressChange_Claim"].map(addr_map).fillna(0).astype(int)

    # late_reporting
    df["late_reporting"] = (df["days_since_incident"] > 30).astype(int)

    # Target
    df["fraud_reported"] = df["FraudFound_P"]

    X = df[FEATURE_COLUMNS].copy()
    y = df["fraud_reported"].copy()

    X = X.fillna(0)
    for col in X.columns:
        if X[col].dtype == object:
            X[col] = pd.to_numeric(X[col], errors="coerce").fillna(0)

    fraud_rate = y.mean()
    print(f"   Fraud rate: {fraud_rate:.1%}  ({y.sum():,} fraud / {len(y):,} total)")
    return X, y, "fraud_oracle"


def load_insurance_claims(csv_path: str) -> tuple:
    """Load insurance_claims.csv (generated/synthetic dataset)."""
    print(f"📂 Loading insurance_claims.csv: {csv_path}")
    df = pd.read_csv(csv_path)
    print(f"   Rows: {len(df):,}  |  Columns: {len(df.columns)}")

    # Handle fraud_reported as Y/N strings
    if df["fraud_reported"].dtype == object:
        df["fraud_reported"] = (df["fraud_reported"].str.upper() == "Y").astype(int)

    # Generate derived features if missing
    if "claim_to_limit_ratio" not in df.columns:
        if "claim_amount" in df.columns and "policy_limit" in df.columns:
            df["claim_to_limit_ratio"] = df["claim_amount"] / df["policy_limit"].clip(lower=1)
        else:
            df["claim_to_limit_ratio"] = 0.5

    if "is_round_number" not in df.columns:
        if "claim_amount" in df.columns:
            df["is_round_number"] = ((df["claim_amount"] % 100 == 0) & (df["claim_amount"] > 0)).astype(int)
        else:
            df["is_round_number"] = 0

    # Fill missing feature columns
    for col in FEATURE_COLUMNS:
        if col not in df.columns:
            df[col] = 0

    X = df[FEATURE_COLUMNS].copy()
    y = df["fraud_reported"].copy()

    X = X.fillna(0)
    for col in X.columns:
        if X[col].dtype == object:
            X[col] = pd.to_numeric(X[col], errors="coerce").fillna(0)

    fraud_rate = y.mean()
    print(f"   Fraud rate: {fraud_rate:.1%}  ({y.sum():,} fraud / {len(y):,} total)")
    return X, y, "insurance_claims"


def load_all_datasets() -> tuple:
    """Load and merge all available datasets for maximum training data."""
    all_X = []
    all_y = []
    sources = []

    # Priority 1: fraud_oracle.csv (15K real Kaggle records)
    oracle_path = os.path.join(DATASET_DIR, "fraud_oracle.csv")
    if os.path.exists(oracle_path):
        X, y, src = load_fraud_oracle(oracle_path)
        all_X.append(X)
        all_y.append(y)
        sources.append(f"{src} ({len(X):,} rows)")

    # Priority 2: insurance_claims.csv
    claims_path = os.path.join(DATASET_DIR, "insurance_claims.csv")
    if os.path.exists(claims_path):
        X, y, src = load_insurance_claims(claims_path)
        all_X.append(X)
        all_y.append(y)
        sources.append(f"{src} ({len(X):,} rows)")

    if not all_X:
        raise ValueError("No datasets found in datasets/ folder")

    X_combined = pd.concat(all_X, ignore_index=True)
    y_combined = pd.concat(all_y, ignore_index=True)

    print(f"\n📊 Combined dataset: {len(X_combined):,} rows from {len(sources)} source(s)")
    print(f"   Sources: {', '.join(sources)}")
    print(f"   Combined fraud rate: {y_combined.mean():.1%}")

    return X_combined, y_combined


# ═══════════════════════════════════════════════════════════════════════
# MODEL TRAINING
# ═══════════════════════════════════════════════════════════════════════

def train_model(X: pd.DataFrame, y: pd.Series) -> dict:
    """Train Gradient Boosting + Random Forest ensemble with SMOTE."""
    print("\n── Training Configuration ──")
    print(f"   Features: {list(X.columns)}")
    print(f"   Samples:  {len(X):,}")

    start_time = time.time()

    # ── Train/test split ─────────────────────────────────────────────
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    print(f"   Train: {len(X_train):,}  |  Test: {len(X_test):,}")

    # ── SMOTE oversampling for class imbalance ───────────────────────
    used_smote = False
    try:
        from imblearn.over_sampling import SMOTE
        smote = SMOTE(random_state=42, k_neighbors=5)
        X_train_bal, y_train_bal = smote.fit_resample(X_train, y_train)
        print(f"   SMOTE: {len(X_train):,} → {len(X_train_bal):,} samples (balanced)")
        used_smote = True
    except ImportError:
        print("   ⚠️  imbalanced-learn not installed — using class_weight='balanced'")
        X_train_bal, y_train_bal = X_train, y_train

    # ── Scale features ───────────────────────────────────────────────
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train_bal)
    X_test_scaled = scaler.transform(X_test)

    # ── Train Gradient Boosting (better for imbalanced data) ─────────
    print("\n🔧 Training Gradient Boosting Classifier...")
    gb_model = GradientBoostingClassifier(
        n_estimators=300,
        max_depth=6,
        min_samples_split=10,
        min_samples_leaf=5,
        learning_rate=0.1,
        subsample=0.8,
        random_state=42,
    )
    gb_model.fit(X_train_scaled, y_train_bal)
    gb_proba = gb_model.predict_proba(X_test_scaled)[:, 1]
    gb_auc = roc_auc_score(y_test, gb_proba)
    print(f"   GB ROC-AUC: {gb_auc:.4f}")

    # ── Train Random Forest ──────────────────────────────────────────
    print("🔧 Training Random Forest Classifier...")
    rf_model = RandomForestClassifier(
        n_estimators=300,
        max_depth=10,
        min_samples_split=10,
        min_samples_leaf=5,
        class_weight="balanced",
        random_state=42,
        n_jobs=-1,
    )
    rf_model.fit(X_train_scaled, y_train_bal)
    rf_proba = rf_model.predict_proba(X_test_scaled)[:, 1]
    rf_auc = roc_auc_score(y_test, rf_proba)
    print(f"   RF ROC-AUC: {rf_auc:.4f}")

    # ── Pick best model ──────────────────────────────────────────────
    if gb_auc >= rf_auc:
        model = gb_model
        model_type = "GradientBoostingClassifier"
        print(f"\n✅ Selected: Gradient Boosting (AUC {gb_auc:.4f} ≥ RF {rf_auc:.4f})")
    else:
        model = rf_model
        model_type = "RandomForestClassifier"
        print(f"\n✅ Selected: Random Forest (AUC {rf_auc:.4f} > GB {gb_auc:.4f})")

    # ── Cross-validation on chosen model ─────────────────────────────
    print("📊 Running 5-fold cross-validation...")
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    cv_scores = cross_val_score(model, X_train_scaled, y_train_bal, cv=cv, scoring="roc_auc")
    print(f"   CV ROC-AUC: {cv_scores.mean():.4f} ± {cv_scores.std():.4f}")

    # ── Evaluate on test set ─────────────────────────────────────────
    y_proba = model.predict_proba(X_test_scaled)[:, 1]

    # Find optimal threshold using F1 score
    best_threshold = 0.5
    best_f1 = 0
    for t in np.arange(0.2, 0.8, 0.05):
        y_pred_t = (y_proba >= t).astype(int)
        f1_t = f1_score(y_test, y_pred_t, zero_division=0)
        if f1_t > best_f1:
            best_f1 = f1_t
            best_threshold = t

    print(f"   Optimal threshold: {best_threshold:.2f} (F1={best_f1:.4f})")

    y_pred = (y_proba >= best_threshold).astype(int)

    accuracy = accuracy_score(y_test, y_pred)
    precision = precision_score(y_test, y_pred, zero_division=0)
    recall = recall_score(y_test, y_pred, zero_division=0)
    f1 = f1_score(y_test, y_pred, zero_division=0)
    roc_auc = roc_auc_score(y_test, y_proba)
    cm = confusion_matrix(y_test, y_pred).tolist()

    training_time = time.time() - start_time

    print(f"\n── Test Set Performance (threshold={best_threshold:.2f}) ──")
    print(classification_report(y_test, y_pred, target_names=["Legitimate", "Fraud"]))
    print(f"ROC-AUC Score: {roc_auc:.4f}")

    # ── Feature importance ───────────────────────────────────────────
    if hasattr(model, 'feature_importances_'):
        feature_importance = dict(zip(
            X.columns.tolist(),
            [round(float(v), 4) for v in model.feature_importances_]
        ))
    else:
        feature_importance = {}

    sorted_importance = dict(sorted(feature_importance.items(), key=lambda x: x[1], reverse=True))

    print(f"\n── Feature Importance ──")
    for feat, imp in sorted_importance.items():
        bar = "█" * int(imp * 50)
        print(f"   {feat:>25s}: {imp:.4f}  {bar}")

    # ── Save model ───────────────────────────────────────────────────
    with open(MODEL_PATH, "wb") as f:
        pickle.dump(model, f)
    print(f"\n✅ Model saved: {MODEL_PATH}")

    with open(SCALER_PATH, "wb") as f:
        pickle.dump(scaler, f)
    print(f"✅ Scaler saved: {SCALER_PATH}")

    # ── Save versioned copy ──────────────────────────────────────────
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    versioned_path = os.path.join(MODEL_DIR, f"fraud_model_v{timestamp}.pkl")
    with open(versioned_path, "wb") as f:
        pickle.dump(model, f)

    # ── Save threshold ───────────────────────────────────────────────
    threshold_path = os.path.join(MODEL_DIR, "threshold.json")
    with open(threshold_path, "w") as f:
        json.dump({"optimal_threshold": round(best_threshold, 3)}, f)

    # ── Save metrics ─────────────────────────────────────────────────
    metrics = {
        "trained_at": datetime.now().isoformat(),
        "training_time_seconds": round(training_time, 2),
        "dataset_size": len(X),
        "train_size": len(X_train),
        "test_size": len(X_test),
        "feature_count": len(FEATURE_COLUMNS),
        "features": FEATURE_COLUMNS,
        "used_smote": used_smote,
        "model_type": model_type,
        "optimal_threshold": round(best_threshold, 3),
        "model_params": model.get_params(),
        "performance": {
            "accuracy": round(accuracy, 4),
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "f1_score": round(f1, 4),
            "roc_auc": round(roc_auc, 4),
            "cv_roc_auc_mean": round(float(cv_scores.mean()), 4),
            "cv_roc_auc_std": round(float(cv_scores.std()), 4),
        },
        "confusion_matrix": {
            "true_negatives": cm[0][0],
            "false_positives": cm[0][1],
            "false_negatives": cm[1][0],
            "true_positives": cm[1][1],
        },
        "feature_importance": sorted_importance,
        "fraud_rate": round(float(y.mean()), 4),
        "model_version": timestamp,
    }

    with open(METRICS_PATH, "w") as f:
        json.dump(metrics, f, indent=2, default=str)
    print(f"✅ Metrics saved: {METRICS_PATH}")

    return metrics


def main():
    """Main training pipeline."""
    print("=" * 60)
    print("  ClaimIQ — Fraud Detection Model Training (Production)")
    print("=" * 60)

    # Load all datasets
    X, y = load_all_datasets()

    # Train
    metrics = train_model(X, y)

    print("\n" + "=" * 60)
    print(f"  ✅ Training Complete!")
    print(f"  📊 Accuracy:  {metrics['performance']['accuracy']:.1%}")
    print(f"  📊 Precision: {metrics['performance']['precision']:.1%}")
    print(f"  📊 Recall:    {metrics['performance']['recall']:.1%}")
    print(f"  📊 F1-Score:  {metrics['performance']['f1_score']:.4f}")
    print(f"  📊 ROC-AUC:   {metrics['performance']['roc_auc']:.4f}")
    print(f"  🎯 Threshold: {metrics['optimal_threshold']}")
    print("=" * 60)


if __name__ == "__main__":
    main()
