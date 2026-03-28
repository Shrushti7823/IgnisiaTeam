"""
ClaimIQ - Quick Start Runner
Run: python run.py
"""
import subprocess
import sys
import os

if __name__ == "__main__":
    print("=" * 50)
    print("  ⚡ ClaimIQ — Starting Server")
    print("=" * 50)
    print("  API Docs:  http://localhost:8000/api/docs")
    print("  Frontend:  Open frontend/pages/index.html")
    print("  Press Ctrl+C to stop")
    print("=" * 50)

    os.environ.setdefault("PYTHONPATH", os.path.dirname(__file__))

    try:
        subprocess.run([
            sys.executable, "-m", "uvicorn",
            "backend.main:app",
            "--host", "0.0.0.0",
            "--port", "8000",
            "--reload",
            "--reload-dir", "backend",
        ])
    except KeyboardInterrupt:
        print("\n👋 ClaimIQ server stopped.")
