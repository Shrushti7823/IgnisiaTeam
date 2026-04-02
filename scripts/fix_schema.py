"""Fix SQLite schema - add missing columns to claims table."""
import sqlite3
import os

db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "claimiq.db")
print(f"Fixing database: {db_path}")

conn = sqlite3.connect(db_path)
cur = conn.cursor()

# Get existing columns
cur.execute("PRAGMA table_info(claims)")
existing = {r[1] for r in cur.fetchall()}
print(f"Existing columns: {len(existing)}")

# Columns to add (name -> SQL type)
new_cols = [
    ("current_stage", "VARCHAR(50) DEFAULT 'submitted'"),
    ("explainability_report", "TEXT"),
    ("stage_doc_verified_at", "DATETIME"),
    ("stage_fraud_analyzed_at", "DATETIME"),
    ("stage_risk_scored_at", "DATETIME"),
    ("stage_decision_at", "DATETIME"),
    ("stage_settled_at", "DATETIME"),
]

added = 0
for col, dtype in new_cols:
    if col not in existing:
        sql = f"ALTER TABLE claims ADD COLUMN {col} {dtype}"
        cur.execute(sql)
        print(f"  + Added: {col} ({dtype})")
        added += 1
    else:
        print(f"  = Exists: {col}")

# Also check users table for any missing columns
cur.execute("PRAGMA table_info(users)")
user_cols = {r[1] for r in cur.fetchall()}
print(f"\nUser columns: {len(user_cols)}")

# Check documents table
cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = [r[0] for r in cur.fetchall()]
print(f"\nTables: {tables}")

# Check if fraud_alerts table exists and has all columns
if "fraud_alerts" in tables:
    cur.execute("PRAGMA table_info(fraud_alerts)")
    fa_cols = {r[1] for r in cur.fetchall()}
    print(f"fraud_alerts columns: {len(fa_cols)}")
    
    fa_new = [
        ("is_resolved", "BOOLEAN DEFAULT 0"),
        ("resolved_by", "VARCHAR(100)"),
        ("resolved_at", "DATETIME"),
    ]
    for col, dtype in fa_new:
        if col not in fa_cols:
            cur.execute(f"ALTER TABLE fraud_alerts ADD COLUMN {col} {dtype}")
            print(f"  + Added to fraud_alerts: {col}")
            added += 1

conn.commit()
conn.close()
print(f"\nDone! Added {added} columns.")
