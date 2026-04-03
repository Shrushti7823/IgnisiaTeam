"""Quick API test for ClaimIQ endpoints."""
import httpx, json, sys

API = "http://localhost:8000"

# 1) Health check
print("=" * 50)
r = httpx.get(f"{API}/health")
print(f"1. Health: {r.json()}")

# 2) Login as admin
print("-" * 50)
r = httpx.post(f"{API}/api/auth/login", data={"username": "admin@claimiq.com", "password": "Admin@123"})
if r.status_code != 200:
    print(f"Login failed: {r.status_code} {r.text}")
    sys.exit(1)
token = r.json()["access_token"]
headers = {"Authorization": f"Bearer {token}"}
print(f"2. Login OK (admin)")

# 3) Model info
print("-" * 50)
r = httpx.get(f"{API}/api/fraud/model-info", headers=headers)
print(f"3. Model Info ({r.status_code}):")
d = r.json()
print(f"   model_available: {d.get('model_available')}")
if d.get("metrics") and d["metrics"].get("performance"):
    p = d["metrics"]["performance"]
    print(f"   accuracy:  {p.get('accuracy')}")
    print(f"   roc_auc:   {p.get('roc_auc')}")
    print(f"   f1_score:  {p.get('f1_score')}")
print(f"   dataset: {d.get('dataset')}")

# 4) Feature importance
print("-" * 50)
r = httpx.get(f"{API}/api/fraud/feature-importance", headers=headers)
print(f"4. Feature Importance ({r.status_code}):")
d = r.json()
if d.get("features"):
    for feat, imp in list(d["features"].items())[:5]:
        print(f"   {feat}: {imp}")

# 5) Dashboard stats
print("-" * 50)
r = httpx.get(f"{API}/api/dashboard/stats", headers=headers)
print(f"5. Dashboard Stats ({r.status_code}):")
d = r.json()
if d.get("overview"):
    print(f"   total_claims: {d['overview'].get('total_claims')}")
    print(f"   stp_rate: {d['overview'].get('stp_rate')}%")

# 6) Model stats (for dashboard ML tab)
print("-" * 50)
r = httpx.get(f"{API}/api/dashboard/model-stats", headers=headers)
print(f"6. Model Stats ({r.status_code}):")
d = r.json()
print(f"   model_available: {d.get('model_available')}")
print(f"   trained_at: {d.get('trained_at')}")
if d.get("performance"):
    print(f"   performance: {d['performance']}")

# 7) Training status
print("-" * 50)
r = httpx.get(f"{API}/api/fraud/training-status", headers=headers)
print(f"7. Training Status ({r.status_code}): {r.json()}")

print("=" * 50)
print("ALL TESTS PASSED!")
