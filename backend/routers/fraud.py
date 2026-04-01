"""
ClaimIQ - Fraud Router
Model management: retraining, metrics, feature importance, dataset upload.
Plus: GET /score/{claim_id} for per-claim fraud analytics.
"""
import os
import sys
import json
import subprocess
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, UploadFile, File
from sqlalchemy.orm import Session

from backend.core.database import get_db
from backend.core.security import get_current_admin, get_current_user
from backend.core.config import settings
from backend.models.user import User
from backend.models.claim import Claim
from backend.models.document import FraudAlert
from backend.ml.fraud_engine import (
    get_training_metrics,
    get_feature_importances,
    is_model_available,
)

router = APIRouter()

# ── Global training state ────────────────────────────────────────────
_training_state = {
    "status": "idle",       # idle | training | complete | error
    "started_at": None,
    "completed_at": None,
    "error": None,
    "progress": 0,
}


def _run_training_bg():
    """Background task: runs model training."""
    global _training_state
    _training_state["status"] = "training"
    _training_state["started_at"] = datetime.now().isoformat()
    _training_state["error"] = None
    _training_state["progress"] = 10

    try:
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        
        # Step 1: Ensure dataset exists
        _training_state["progress"] = 20
        dataset_path = os.path.join(base_dir, "datasets", "insurance_claims.csv")
        if not os.path.exists(dataset_path):
            print("[Retrain] No dataset found — generating...")
            gen_script = os.path.join(base_dir, "scripts", "generate_dataset.py")
            result = subprocess.run(
                [sys.executable, gen_script],
                cwd=base_dir,
                capture_output=True, text=True, timeout=120,
            )
            if result.returncode != 0:
                raise RuntimeError(f"Dataset generation failed: {result.stderr}")
        
        _training_state["progress"] = 40

        # Step 2: Run training
        print("[Retrain] Starting model training...")
        result = subprocess.run(
            [sys.executable, "-m", "backend.ml.train_model"],
            cwd=base_dir,
            capture_output=True, text=True, timeout=300,
        )
        
        _training_state["progress"] = 90

        if result.returncode != 0:
            raise RuntimeError(f"Training failed: {result.stderr}")

        print(f"[Retrain] Training output:\n{result.stdout}")

        _training_state["status"] = "complete"
        _training_state["completed_at"] = datetime.now().isoformat()
        _training_state["progress"] = 100
        print("[Retrain] ✅ Training complete!")

    except Exception as e:
        _training_state["status"] = "error"
        _training_state["error"] = str(e)
        _training_state["progress"] = 0
        print(f"[Retrain] ❌ Training error: {e}")


@router.post("/retrain")
async def retrain_model(
    background_tasks: BackgroundTasks,
    admin: User = Depends(get_current_admin),
):
    """Admin: trigger model retraining on the current dataset."""
    global _training_state
    
    if _training_state["status"] == "training":
        raise HTTPException(
            status_code=409,
            detail="Training already in progress. Please wait."
        )
    
    _training_state = {
        "status": "training",
        "started_at": datetime.now().isoformat(),
        "completed_at": None,
        "error": None,
        "progress": 5,
    }
    
    background_tasks.add_task(_run_training_bg)
    
    return {
        "message": "Model retraining started in background",
        "status": "training",
        "started_at": _training_state["started_at"],
    }


@router.get("/training-status")
async def training_status():
    """Get current training job status."""
    return _training_state


@router.get("/model-info")
async def model_info():
    """Get current model information and training metrics."""
    metrics = get_training_metrics()
    model_available = is_model_available()
    
    # Get dataset info
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    dataset_path = os.path.join(base_dir, "datasets", "insurance_claims.csv")
    dataset_exists = os.path.exists(dataset_path)
    dataset_size = 0
    if dataset_exists:
        try:
            import pandas as pd
            df = pd.read_csv(dataset_path)
            dataset_size = len(df)
        except Exception:
            dataset_size = -1
    
    return {
        "model_available": model_available,
        "model_path": settings.FRAUD_MODEL_PATH,
        "training_status": _training_state["status"],
        "metrics": metrics,
        "dataset": {
            "exists": dataset_exists,
            "path": dataset_path if dataset_exists else None,
            "size": dataset_size,
        },
    }


@router.get("/feature-importance")
async def feature_importance():
    """Get feature importance from the trained model."""
    importances = get_feature_importances()
    if not importances:
        return {
            "available": False,
            "message": "No trained model found. Train the model first.",
            "features": {},
        }
    
    return {
        "available": True,
        "features": importances,
    }


@router.post("/upload-dataset")
async def upload_dataset(
    file: UploadFile = File(...),
    admin: User = Depends(get_current_admin),
):
    """Admin: upload a new CSV dataset for training."""
    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV files are accepted")
    
    content = await file.read()
    size_mb = len(content) / (1024 * 1024)
    if size_mb > 100:
        raise HTTPException(status_code=400, detail="File too large (max 100MB)")
    
    # Save to datasets folder
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    save_path = os.path.join(base_dir, "datasets", "insurance_claims.csv")
    os.makedirs(os.path.dirname(save_path), exist_ok=True)
    
    with open(save_path, "wb") as f:
        f.write(content)
    
    # Validate CSV
    try:
        import pandas as pd
        df = pd.read_csv(save_path)
        row_count = len(df)
        col_count = len(df.columns)
        columns = list(df.columns)
    except Exception as e:
        os.remove(save_path)
        raise HTTPException(status_code=400, detail=f"Invalid CSV: {e}")
    
    return {
        "message": f"Dataset uploaded successfully: {row_count:,} rows, {col_count} columns",
        "file_name": file.filename,
        "rows": row_count,
        "columns": columns,
        "saved_to": save_path,
        "next_step": "Call POST /api/fraud/retrain to train the model on this dataset",
    }


# ── GET /score/{claim_id} — Full fraud score breakdown ───────────────
@router.get("/score/{claim_id}")
def get_fraud_score(
    claim_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get complete fraud score breakdown for a claim:
    hard rules, soft score, ML probability, image fraud, triggered alerts.
    """
    claim = db.query(Claim).filter(Claim.id == claim_id).first()
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")

    if claim.user_id != current_user.id and current_user.role not in ["admin", "adjuster"]:
        raise HTTPException(status_code=403, detail="Access denied")

    # Get fraud alerts
    alerts = [
        {
            "rule_id": a.rule_id,
            "rule_name": a.rule_name,
            "severity": a.severity,
            "description": a.description,
            "score_impact": a.score_impact,
        }
        for a in (claim.fraud_alerts or [])
    ]

    return {
        "claim_id": claim.id,
        "claim_reference": claim.claim_reference,
        "scores": {
            "fraud_score": claim.fraud_score,
            "risk_score": claim.risk_score,
            "confidence_score": claim.confidence_score,
        },
        "production_scores": {
            "hard_rule_violated": claim.hard_rule_violated,
            "soft_rule_score": claim.soft_rule_score,
            "ml_fraud_probability": claim.ml_fraud_probability,
        },
        "image_fraud": {
            "duplicate_image_detected": claim.duplicate_image_detected,
        },
        "triggered_alerts": alerts,
        "alerts_count": len(alerts),
        "decision": claim.status,
        "fraud_cleared": claim.fraud_cleared,
    }
