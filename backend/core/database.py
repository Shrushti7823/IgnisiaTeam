"""
ClaimIQ - Database Connection
Supports MySQL (production) and SQLite (fallback)
"""
from sqlalchemy import create_engine, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from backend.core.config import settings

db_url = settings.DATABASE_URL

# Try MySQL first, fall back to SQLite if connection fails
connect_args = {}
if db_url.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

try:
    engine = create_engine(
        db_url,
        connect_args=connect_args,
        echo=False,
        pool_pre_ping=True,
        pool_recycle=3600,
    )
    # Test the connection
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    print(f"  ✅ Database connected: {db_url.split('@')[-1] if '@' in db_url else db_url}")
except Exception as e:
    print(f"  ⚠️  MySQL connection failed: {e}")
    print("  ⚠️  Falling back to SQLite...")
    db_url = "sqlite:///./claimiq.db"
    connect_args = {"check_same_thread": False}
    engine = create_engine(
        db_url,
        connect_args=connect_args,
        echo=False,
        pool_pre_ping=True,
    )
    print("  ✅ SQLite database connected: claimiq.db")

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    """Dependency - yields a DB session and closes it after request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_new_session():
    """Create a standalone DB session for background tasks."""
    return SessionLocal()
