from sqlalchemy.orm import Session
from app.models.task import Task
from app.models.stopwatch import Stopwatch
from app.models.state import TimerStatus
from datetime import datetime, timezone
import uuid

class TimerService:
    def __init__(self, db: Session):
        self.db = db

    def start_stopwatch(self, task_id: uuid.UUID, start_time: datetime | None = None):
        task = self.db.query(Task).filter(Task.id == task_id).first()
        if not task:
            raise ValueError("Task not found")

        existing_stopwatch = self.db.query(Stopwatch).filter(Stopwatch.task_id == task_id).first()
        if existing_stopwatch:
            raise ValueError("Stopwatch already exists for this task")

        if start_time is None:
            start_time = datetime.now(timezone.utc)

        stopwatch = Stopwatch(
            task_id=task_id,
            status=TimerStatus.RUNNING,
            quantity=0, # Quantity will be set at stop
            accumulated_duration=0,
            created_at=start_time
        )
        self.db.add(stopwatch)
        self.db.commit()
        self.db.refresh(stopwatch)
        return stopwatch

    def pause_stopwatch(self, task_id: uuid.UUID):
        
        stopwatch = self.db.query(Stopwatch).filter(
            Stopwatch.task_id == task_id,
            Stopwatch.status == TimerStatus.RUNNING
        ).first()

        if not stopwatch:
            raise ValueError("No running stopwatch found for this task")

        now = datetime.now(timezone.utc)
        last_start_time = stopwatch.update_at or stopwatch.created_at
        elapsed_time = (now - last_start_time).total_seconds() * 1000 # milliseconds

        stopwatch.accumulated_duration += int(elapsed_time)
        stopwatch.status = TimerStatus.PAUSED
        stopwatch.update_at = now

        self.db.commit()
        self.db.refresh(stopwatch)
        return stopwatch

    def resume_stopwatch(self, task_id: uuid.UUID):
        stopwatch = self.db.query(Stopwatch).filter(
            Stopwatch.task_id == task_id,
            Stopwatch.status == TimerStatus.PAUSED
        ).first()

        if not stopwatch:
            raise ValueError("No paused stopwatch found for this task")

        now = datetime.now(timezone.utc)
        stopwatch.status = TimerStatus.RUNNING
        stopwatch.update_at = now

        self.db.commit()
        self.db.refresh(stopwatch)
        return stopwatch

    def stop_stopwatch(self, task_id: uuid.UUID, real_quantity: float):
        stopwatch = self.db.query(Stopwatch).filter(Stopwatch.task_id == task_id).first()

        if not stopwatch:
            raise ValueError("No stopwatch found for this task")

        if stopwatch.status == TimerStatus.STOPPED:
            raise ValueError("Stopwatch is already stopped")

        now = datetime.now(timezone.utc)
        accumulated_duration = stopwatch.accumulated_duration

        if stopwatch.status == TimerStatus.RUNNING:
            last_start_time = stopwatch.update_at or stopwatch.created_at
            elapsed_time = (now - last_start_time).total_seconds() * 1000 # milliseconds
            accumulated_duration += int(elapsed_time)

        # Create a record in record_stopwatch
        record = RecordStopwatch(
            task_id=task_id,
            quantity=real_quantity,
            accumulated_duration=accumulated_duration
        )
        self.db.add(record)

        # Delete from stopwatch
        self.db.delete(stopwatch)

        self.db.commit()
        return record
