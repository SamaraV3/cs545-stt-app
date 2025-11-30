from sqlalchemy import Column, Integer, String, DateTime, Text
from datetime import datetime
from database import Base

class Reminder(Base):
    __tablename__= "reminders"
    id = Column(Integer, primary_key=True, index=True)
    task = Column(Text)
    time_iso = Column(String)
    repeat = Column(String, nullable=True)
    status = Column(String)
    created_at = Column(String)
    updated_at = Column(String)

class EventLog(Base):
    __tablename__ = "event_log"
    id = Column(Integer, primary_key=True, index=True)
    event_type = Column(String)
    reminder_id = Column(Integer)
    timestamp = Column(String, default=lambda: datetime.now().isoformat())
    info = Column(String, nullable=True) #optional details go here