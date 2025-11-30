import threading, time
from database import SessionLocal
import crud
from datetime import datetime

def scheduler_loop():
    while True:
        try:
            db = SessionLocal()
            now = datetime.now().isoformat()
            due_list = crud.get_due_reminders(db, now)
            for reminder in due_list:
                crud.mark_due(db, reminder)
            db.close()
        except Exception as e:
            print("Scheduler error:", e)
        time.sleep(60)#run every min

def start_scheduler():
    thread = threading.Thread(target=scheduler_loop, daemon=True)
    thread.start()