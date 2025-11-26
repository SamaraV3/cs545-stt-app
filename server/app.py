#main fastapi app - will eventually contain stuff for starting the scheduler

from fastapi import FastAPI
from routes.reminders import router as reminders_router
from scheduler import start_scheduler
from contextlib import asynccontextmanager

from database import engine
from models import Base

@asynccontextmanager
async def lifespan(app: FastAPI):
    #create database and tables if they dont exist
    Base.metadata.create_all(bind=engine)
    start_scheduler()
    yield

app = FastAPI(lifespan=lifespan)
app.include_router(reminders_router)