"""
ClaimIQ - Configuration Settings
Enterprise Edition
"""
from pydantic_settings import BaseSettings
from typing import Optional
import os


class Settings(BaseSettings):
    # App
    APP_NAME: str = "ClaimIQ"
    APP_VERSION: str = "2.0.0"
    DEBUG: bool = True

    # Database - MySQL (production) / SQLite (fallback)
    DATABASE_URL: str = "mysql+pymysql://root:root@localhost:3306/claimiq"

    # Security
    SECRET_KEY: str = "claimiq-secret-key-change-in-production-2024"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours

    # File Upload
    UPLOAD_DIR: str = "./uploads"
    MAX_FILE_SIZE_MB: int = 10

    # STP Thresholds (legacy — kept for backward compat)
    STP_AMOUNT_LIMIT: float = 5000.0
    FRAUD_SCORE_THRESHOLD: float = 70.0
    AUTO_APPROVE_SCORE: float = 30.0

    # ── Production Rule Engine Thresholds ─────────────
    # ML fraud probability (0–1 scale)
    ML_REJECT_THRESHOLD: float = 0.8
    ML_REVIEW_THRESHOLD: float = 0.5

    # Soft-rule score thresholds (0–100 scale, higher = safer)
    SOFT_SCORE_AUTO_APPROVE: float = 70.0
    SOFT_SCORE_REJECT: float = 40.0

    # Image hashing — max Hamming distance for "duplicate" match
    IMAGE_HASH_DISTANCE_THRESHOLD: int = 5

    # ML Model paths
    FRAUD_MODEL_PATH: str = "./backend/ml/models/fraud_model.pkl"

    # Google Gemini API
    GEMINI_API_KEY: str = ""

    # Pipeline simulation delays (seconds) - for demo effect
    PIPELINE_STAGE_DELAY: float = 1.5

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()

# Ensure directories exist
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
os.makedirs("./backend/ml/models", exist_ok=True)
