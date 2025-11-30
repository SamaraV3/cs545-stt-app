import requests

BASE = "http://127.0.0.1:8000"

# 1. Create a reminder
print("Creating reminder...")
r = requests.post(
    f"{BASE}/reminders/",
    json={
        "task": "Test reminder from script",
        "time_iso": "2025-01-01T12:00:00",
        "repeat": None
    }
)
print("POST /reminders:", r.status_code, r.json())

# 2. List reminders
print("\nListing reminders...")
r = requests.get(f"{BASE}/reminders/")
print("GET /reminders:", r.status_code, r.json())

# 3. Delete first reminder (if exists)
reminders = r.json()
if reminders:
    first_id = reminders[0]["id"]
    print(f"\nDeleting reminder {first_id}...")
    r = requests.delete(f"{BASE}/reminders/{first_id}")
    print("DELETE /reminders/{id}:", r.status_code, r.json())

# 4. List reminders again
print("\nListing reminders after delete...")
r = requests.get(f"{BASE}/reminders/")
print("GET /reminders:", r.status_code, r.json())