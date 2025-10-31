from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.dependency import get_db
from app.models.task import Task
from app.models.record_stopwatch import RecordStopwatch as RecordStopwatchModel
from app.schemas.record_stopwatch import RecordStopwatch, RecordStopwatchUpdate, RecordStopwatchStart
from datetime import datetime
import uuid

router = APIRouter()