import threading, time
from database import SessionLocal
import crud
from datetime import datetime

def scheduler_loop():
    while True:
        db = SessionLocal()
        now = datetime.now().isoformat()
        due = crud.get_due_reminders(db, now)
        #will eventually mark due + log events
        db.close()
        time.sleep(60)

def start_scheduler():
    thread = threading.Thread(target=scheduler_loop, daemon=True)
    thread.start()