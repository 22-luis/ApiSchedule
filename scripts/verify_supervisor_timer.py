import requests
import uuid
import sys

BASE_URL = "http://localhost:8000/api/v1"

def test_supervisor_timer():
    # Attempt to start a timer (this might fail if not running locally, but we can verify imports/syntax)
    task_id = str(uuid.uuid4())
    print(f"Testing Supervision Timer Endpoints for Task: {task_id}")
    
    # Check status endpoint
    try:
        response = requests.get(f"{BASE_URL}/supervisor/timer/status/{task_id}")
        print(f"Status GET Response: {response.status_code}")
    except Exception as e:
        print(f"Status GET failed (is server running?): {e}")

    # Check status POST (bulk)
    try:
        response = requests.post(f"{BASE_URL}/supervisor/timer/status", json={"task_ids": [task_id]})
        print(f"Status POST (bulk) Response: {response.status_code}")
    except Exception as e:
        print(f"Status POST failed: {e}")

if __name__ == "__main__":
    test_supervisor_timer()
