"""
ClaimIQ — Realistic Insurance Fraud Dataset Generator
Generates a 10,000-row CSV modeled on real Kaggle insurance fraud datasets.

Run: python scripts/generate_dataset.py

The generated CSV can be used to train the fraud detection model.
If you have a real Kaggle CSV, place it in datasets/ and the training
script will auto-detect and use it instead.
"""
import os
import sys
import numpy as np
import pandas as pd
from datetime import datetime, timedelta

np.random.seed(42)

# ── Configuration ────────────────────────────────────────────────────
N = 10000
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "datasets")
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "insurance_claims.csv")
os.makedirs(OUTPUT_DIR, exist_ok=True)

print(f"🔧 Generating {N:,} realistic insurance claim records...\n")

# ── Policy-level features ────────────────────────────────────────────
policy_types = np.random.choice(
    ["auto", "health", "travel", "property"],
    size=N,
    p=[0.40, 0.30, 0.15, 0.15],
)

policy_limits = {
    "auto":     np.random.choice([5000, 10000, 15000, 20000, 25000], size=N, p=[0.30, 0.35, 0.20, 0.10, 0.05]),
    "health":   np.random.choice([10000, 25000, 50000, 100000], size=N, p=[0.25, 0.35, 0.25, 0.15]),
    "travel":   np.random.choice([2000, 3000, 5000, 10000], size=N, p=[0.30, 0.35, 0.25, 0.10]),
    "property": np.random.choice([10000, 25000, 50000, 75000, 100000], size=N, p=[0.20, 0.30, 0.25, 0.15, 0.10]),
}
policy_limit = np.array([policy_limits[pt][i] for i, pt in enumerate(policy_types)], dtype=float)

policy_age_days = np.random.exponential(scale=500, size=N).astype(int).clip(1, 3650)

# ── Claim-level features ────────────────────────────────────────────
# Claim types map to policy types
claim_type_map = {
    "auto":     ["collision", "theft", "vandalism", "glass_damage", "total_loss"],
    "health":   ["hospitalization", "surgery", "outpatient", "emergency", "dental"],
    "travel":   ["flight_cancel", "lost_luggage", "medical_abroad", "trip_interrupt"],
    "property": ["fire", "water_damage", "theft", "natural_disaster", "structural"],
}
incident_types = []
for pt in policy_types:
    incident_types.append(np.random.choice(claim_type_map[pt]))
incident_types = np.array(incident_types)

# Claim amounts — follow log-normal distribution (realistic)
base_amounts = np.random.lognormal(mean=7.0, sigma=0.8, size=N).clip(100, 200000)
# Scale to be proportional to policy limit
claim_amount = np.minimum(base_amounts, policy_limit * 1.2)
claim_amount = np.round(claim_amount, 2)

# Derived features
claim_to_limit_ratio = claim_amount / np.maximum(policy_limit, 1)
is_round_amount = ((claim_amount % 100 == 0) & (claim_amount > 0)).astype(int)

# Prior claims — Poisson distribution
prior_claims = np.random.poisson(lam=0.8, size=N).clip(0, 15)

# Prior fraud flags — rare, ~5%
prior_fraud_flags = np.random.binomial(1, 0.05, size=N)

# Days since incident — exponential (most claims filed quickly)
days_since_incident = np.random.exponential(scale=12, size=N).astype(int).clip(0, 365)

# Is weekend
is_weekend = np.random.binomial(1, 0.286, size=N)  # 2/7 days

# Document count
document_count = np.random.choice([0, 1, 2, 3, 4, 5], size=N, p=[0.05, 0.15, 0.30, 0.25, 0.15, 0.10])

# OCR mismatch — does the OCR-extracted amount differ significantly?
ocr_mismatch = np.random.binomial(1, 0.08, size=N)

# Late reporting (>30 days)
late_reporting = (days_since_incident > 30).astype(int)

# ── Generate fraud labels using realistic rule-based logic ───────────
# This mimics how fraud is detected in real insurance systems
fraud_probability = np.zeros(N)

# High claim-to-limit ratio → very suspicious
fraud_probability += (claim_to_limit_ratio >= 0.90) * 0.25
fraud_probability += (claim_to_limit_ratio >= 0.70) * 0.08

# Multiple prior claims
fraud_probability += (prior_claims >= 3) * 0.20
fraud_probability += (prior_claims >= 2) * 0.10

# Prior fraud flags — biggest indicator
fraud_probability += (prior_fraud_flags > 0) * 0.35

# Same-day filing
fraud_probability += (days_since_incident == 0) * 0.10

# New policy
fraud_probability += (policy_age_days < 30) * 0.15
fraud_probability += (policy_age_days < 90) * 0.05

# Round amounts
fraud_probability += is_round_amount * 0.05

# OCR mismatch
fraud_probability += ocr_mismatch * 0.15

# Late reporting
fraud_probability += late_reporting * 0.05

# No documents
fraud_probability += (document_count == 0) * 0.12

# Weekend
fraud_probability += is_weekend * 0.02

# Add noise
fraud_probability += np.random.normal(0, 0.05, size=N)
fraud_probability = fraud_probability.clip(0, 1)

# Generate binary fraud label
fraud_reported = (np.random.random(N) < fraud_probability).astype(int)

fraud_rate = fraud_reported.mean()
print(f"📊 Fraud rate: {fraud_rate:.1%} ({fraud_reported.sum():,} fraudulent / {N:,} total)")

# ── Build DataFrame ─────────────────────────────────────────────────
df = pd.DataFrame({
    "policy_number":        [f"POL-{i:06d}" for i in range(N)],
    "policy_type":          policy_types,
    "claim_type":           incident_types,
    "incident_type":        incident_types,
    "claim_amount":         claim_amount,
    "policy_limit":         policy_limit,
    "policy_age_days":      policy_age_days,
    "prior_claims":         prior_claims,
    "prior_fraud_flags":    prior_fraud_flags,
    "days_since_incident":  days_since_incident,
    "is_weekend":           is_weekend,
    "is_round_amount":      is_round_amount,
    "document_count":       document_count,
    "ocr_mismatch":         ocr_mismatch,
    "late_reporting":       late_reporting,
    "claim_to_limit_ratio": np.round(claim_to_limit_ratio, 4),
    "fraud_reported":       fraud_reported,
})

# ── Save ────────────────────────────────────────────────────────────
df.to_csv(OUTPUT_FILE, index=False)
print(f"\n✅ Dataset saved to: {OUTPUT_FILE}")
print(f"   Columns: {len(df.columns)}")
print(f"   Rows:    {len(df):,}")

# ── Summary Statistics ──────────────────────────────────────────────
print(f"\n── Feature Summary ──")
print(f"  Claim amounts:  ${df['claim_amount'].mean():,.0f} avg,  ${df['claim_amount'].median():,.0f} median")
print(f"  Policy limits:  ${df['policy_limit'].mean():,.0f} avg")
print(f"  Prior claims:   {df['prior_claims'].mean():.2f} avg")
print(f"  Days to file:   {df['days_since_incident'].mean():.1f} avg")
print(f"  OCR mismatches: {ocr_mismatch.sum():,} ({ocr_mismatch.mean():.1%})")

print(f"\n── Fraud by Policy Type ──")
for pt in ["auto", "health", "travel", "property"]:
    mask = df["policy_type"] == pt
    rate = df.loc[mask, "fraud_reported"].mean()
    count = mask.sum()
    print(f"  {pt:>10s}: {rate:.1%} fraud rate  ({count:,} claims)")

print(f"\n✅ Dataset ready for model training!")
print(f"   Run: python -m backend.ml.train_model")
