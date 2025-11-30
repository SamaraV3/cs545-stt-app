import requests
import time
from datetime import datetime, timedelta

BASE = "http://127.0.0.1:8000"

print("Creating test reminder...")

rem_time = (datetime.now() + timedelta(seconds=5)).isoformat()

payload = {
    "task": "Scheduler Test Reminder",
    "time_iso": rem_time,
    "repeat": None
}

create_res = requests.post(f"{BASE}/reminders/", json=payload)
print("POST raw:", create_res.text)

reminder = create_res.json()
rem_id = reminder["id"]

print("\nCreated reminder with ID:", rem_id)
print("Reminder time:", rem_time)

print("\nWaiting 70 seconds for scheduler loop...")
time.sleep(70)

# Get ALL reminders
after_res = requests.get(f"{BASE}/reminders/")
all_rems = after_res.json()

print("\nAll reminders after scheduler:", all_rems)

# Find our reminder
found = next((r for r in all_rems if r["id"] == rem_id), None)

if not found:
    print("❌ FAILED: Could not find reminder after scheduler.")
else:
    print("Found reminder:", found)
    if found["status"] == "due":
        print("🎉 Scheduler SUCCESS: reminder was marked as due!")
    else:
        print("❌ Scheduler FAILED: reminder status is still:", found["status"])
