import requests
import json

BASE_URL = "http://localhost:8069"
session = requests.Session()

def test_auth():
    print("\n--- Testing Authentication ---")
    payload = {"username": "superadmin", "password": "superadmin123"}
    # The login endpoint expects form data or JSON? 
    # Usually OAuth2PasswordRequestForm expects form data.
    resp = session.post(f"{BASE_URL}/api/auth/login", data=payload)
    if resp.status_code == 200:
        print("[OK] Login successful")
        token = resp.json().get("access_token")
        session.headers.update({"Authorization": f"Bearer {token}"})
        return True
    else:
        print(f"[FAIL] Login failed: {resp.status_code} - {resp.text}")
        return False

def test_endpoint(name, path, method="GET"):
    print(f"--- Testing {name} ({path}) ---")
    resp = session.request(method, f"{BASE_URL}{path}")
    if resp.status_code == 200:
        print(f"[OK] {name} response 200")
        try:
            data = resp.json()
            print(f"[DATA] Keys: {list(data.keys()) if isinstance(data, dict) else 'List'}")
        except:
            print("[INFO] Non-JSON response")
    else:
        print(f"[FAIL] {name} failed: {resp.status_code} - {resp.text}")

if __name__ == "__main__":
    if test_auth():
        test_endpoint("Me Profile", "/api/auth/me")
        test_endpoint("Dashboard Stats", "/api/dashboard/stats")
        test_endpoint("Threads", "/api/threads")
        test_endpoint("Drafts", "/api/drafts")
        test_endpoint("Contacts", "/api/contacts")
        test_endpoint("Calendar", "/api/calendar/events?days=7")
        test_endpoint("Admin Stats", "/api/admin/stats")
        test_endpoint("Admin Users", "/api/admin/users")
        test_endpoint("Admin Audit", "/api/admin/audit")
        test_endpoint("OAuth Status", "/api/oauth/status")
