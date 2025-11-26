from sqlalchemy import Column, Integer, String, DateTime, Text
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