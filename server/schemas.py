from pydantic import BaseModel

class ReminderCreate(BaseModel):
    task: str
    time_iso: str
    repeat: str | None = None

class ReminderRead(BaseModel):
    id: int
    task: str
    time_iso: str
    repeat: str | None
    status: str

    class Config:
        orm_mode = True