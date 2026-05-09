
import requests

BASE_URL = "http://localhost:8069"

endpoints = [
    ("/api/dashboard/stats", "GET"),
    ("/api/emails", "GET"),
    ("/api/threads", "GET"),
    ("/api/contacts", "GET"),
    ("/api/calendar/events", "GET"),
    ("/api/assistant/chat", "POST"),
    ("/api/user/sync-voice", "POST")
]

def check_endpoints():
    print(f"--- STARTING ENDPOINT HEALTH CHECK ---")
    for route, method in endpoints:
        url = f"{BASE_URL}{route}"
        try:
            if method == "GET":
                r = requests.get(url, timeout=5)
            else:
                r = requests.post(url, timeout=5)
            
            # We expect 401 or 403 because we don't have a token, 
            # but 404 or 500 would mean a broken route.
            status = r.status_code
            if status in [401, 403, 405, 200]:
                print(f"[OK] {method} {route} - Status: {status}")
            else:
                print(f"[ERROR] {method} {route} - Status: {status}")
        except Exception as e:
            print(f"[CRITICAL] {method} {route} - Failed to connect: {e}")

if __name__ == "__main__":
    check_endpoints()
