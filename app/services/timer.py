from sqlalchemy.orm import Session
from app.models.task import Task
from app.models.stopwatch import Stopwatch
from app.models.record_stopwatch import RecordStopwatch
from app.models.state import TimerStatus
from datetime import datetime, timezone, timedelta
import uuid
import logging
import sys

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = logging.StreamHandler(sys.stdout)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

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
            start_time = datetime.now(timezone.utc) - timedelta(hours=6)

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
        now = datetime.now(timezone.utc) - timedelta(hours=6)
        
        stopwatch = self.db.query(Stopwatch).filter(
            Stopwatch.task_id == task_id,
            Stopwatch.status == TimerStatus.RUNNING
        ).first()

        if not stopwatch:
            raise ValueError("No running stopwatch found for this task")

        last_start_time = (stopwatch.update_at or stopwatch.created_at).astimezone(timezone.utc)
        elapsed_time = (now - last_start_time).total_seconds() / 3600  # Convert to hours

        stopwatch.accumulated_duration += elapsed_time
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

        now = datetime.now(timezone.utc) - timedelta(hours=6)
        stopwatch.status = TimerStatus.RUNNING
        stopwatch.update_at = now

        self.db.commit()
        self.db.refresh(stopwatch)
        return stopwatch

    def stop_stopwatch(self, task_id: uuid.UUID, real_quantity: float):
        now = datetime.now(timezone.utc) - timedelta(hours=6)
        
        stopwatch = self.db.query(Stopwatch).filter(Stopwatch.task_id == task_id).first()

        if not stopwatch:
            raise ValueError("No stopwatch found for this task")

        if stopwatch.status == TimerStatus.STOPPED:
            raise ValueError("Stopwatch is already stopped")

        accumulated_duration = stopwatch.accumulated_duration

        if stopwatch.status == TimerStatus.RUNNING:
            last_start_time = (stopwatch.update_at or stopwatch.created_at).astimezone(timezone.utc)
            time_difference = now - last_start_time
            elapsed_time = time_difference.total_seconds() / 3600  # Convert to hours
            accumulated_duration += elapsed_time

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

    def get_tasks_status(self, task_ids: list[uuid.UUID]):
        # Get tasks from Stopwatch (running, paused)
        stopwatch_tasks = self.db.query(Stopwatch.task_id, Stopwatch.status).filter(Stopwatch.task_id.in_(task_ids)).all()

        # Get tasks from RecordStopwatch (completed/done)
        record_stopwatch_tasks = self.db.query(RecordStopwatch.task_id).filter(RecordStopwatch.task_id.in_(task_ids)).all()

        # Create a dictionary to hold the status, prioritizing 'done'
        task_statuses = {}

        for task_id, status in stopwatch_tasks:
            task_statuses[str(task_id)] = status.value

        for task_id_record, in record_stopwatch_tasks:
            task_statuses[str(task_id_record)] = TimerStatus.STOPPED.value 

        # Format the output
        return [{"task_id": task_id, "status": status} for task_id, status in task_statuses.items()]
