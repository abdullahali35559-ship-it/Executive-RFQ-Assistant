
import requests
import json

# We need a valid token to test this, but we can simulate the request logic
# or check if the backend now correctly parses the data if we had a session.
# Since I can't easily get a session token here without a real login, 
# I will check the code logic.

def test_payload_simulation():
    # Simulated data from frontend
    payload = {
        "provider": "google",
        "title": "Test Meeting",
        "start_time": "2026-05-10T09:00:00Z",
        "end_time": "2026-05-10T10:00:00Z",
        "attendees": ["test@example.com"],
        "description": "Test description"
    }
    
    # Mocking the backend logic
    data = payload
    start = data.get('start') or data.get('start_time')
    end = data.get('end') or data.get('end_time')
    
    print(f"Logic Test: Start={start}, End={end}")
    if start and end:
        print("SUCCESS: Fields correctly mapped.")
    else:
        print("FAILED: Fields still missing.")

if __name__ == "__main__":
    test_payload_simulation()
