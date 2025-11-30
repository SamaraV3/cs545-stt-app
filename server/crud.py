from sqlalchemy.orm import Session
from models import Reminder, EventLog
from datetime import datetime

def create_reminder(db: Session, task, time_iso, repeat):
    reminder = Reminder(
        task=task,
        time_iso=time_iso,
        repeat=repeat,
        status="scheduled",
        created_at=datetime.now().isoformat(),
        updated_at=datetime.now().isoformat()
    )
    db.add(reminder)
    db.commit()
    db.refresh(reminder)
    log_event(db, "CREATED", reminder.id, info=task)
    return reminder

def list_reminders(db: Session):
    return db.query(Reminder).all()

def delete_reminder(db: Session, reminder_id):
    log_event(db, "DELETED", reminder_id)
    db.query(Reminder).filter(Reminder.id == reminder_id).delete()
    db.commit()

def get_due_reminders(db: Session, now_iso):
    return db.query(Reminder).filter(
        Reminder.time_iso <= now_iso,
        Reminder.status == "scheduled"
    ).all()

def log_event(db, event_type, reminder_id, info=None):
    log = EventLog(
        event_type=event_type,
        reminder_id=reminder_id,
        info=info
    )
    db.add(log)
    db.commit()

def mark_due(db, reminder):
    reminder.status = "due"
    reminder.updated_at = datetime.now().isoformat()
    db.commit()
    db.refresh(reminder)

    log_event(db, "DUE", reminder.id, info=reminder.task)

