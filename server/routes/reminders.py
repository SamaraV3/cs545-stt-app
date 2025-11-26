from fastapi import APIRouter, Depends
from database import SessionLocal
import crud
from schemas import ReminderCreate, ReminderRead

router = APIRouter(prefix="/reminders")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("/", response_model=ReminderRead)
def create(rem: ReminderCreate, db=Depends(get_db)):
    return crud.create_reminder(db, rem.task, rem.time_iso, rem.repeat)

@router.get("/", response_model=list[ReminderRead])
def list_all(db=Depends(get_db)):
    return crud.list_reminders(db)

@router.delete("/{id}")
def delete(id: int, db=Depends(get_db)):
    crud.delete_reminder(db, id)
    return {"ok": True}