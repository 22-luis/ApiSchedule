from sqlalchemy.orm import Session
from sqlalchemy import func
from app.models.task import Task
from app.models.stopwatch import Stopwatch
from app.models.record_stopwatch import RecordStopwatch
from app.models.programming import ProgrammingTask
from app.models.code import Code
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

    def start_stopwatch(self, task_id: uuid.UUID, start_time: datetime | None = None, is_from_programming: bool = False):
        task = self.db.query(Task).filter(Task.id == task_id).first()
        if not task:
            raise ValueError("Task not found")

        existing_stopwatch = self.db.query(Stopwatch).filter(
            Stopwatch.task_id == task_id,
            Stopwatch.is_from_programming == is_from_programming
        ).first()
        if existing_stopwatch:
            raise ValueError("Stopwatch already exists for this task with the same programming flag")

        if start_time is None:
            start_time = datetime.now(timezone.utc) - timedelta(hours=6)

        stopwatch = Stopwatch(
            task_id=task_id,
            status=TimerStatus.RUNNING,
            quantity=0, # Quantity will be set at stop
            accumulated_duration=0,
            is_from_programming=is_from_programming,
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

    def stop_stopwatch(self, task_id: uuid.UUID, real_quantity: float, user_id: uuid.UUID):
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

        record = None
        # Create a record in record_stopwatch or update ProgrammingTask
        if stopwatch.is_from_programming is False:
            record = RecordStopwatch(
                task_id=task_id,
                quantity=real_quantity,
                accumulated_duration=accumulated_duration
            )
            self.db.add(record)
        else:
            record = self.db.query(ProgrammingTask).filter(ProgrammingTask.task_id == task_id).first()
            if not record:
                raise ValueError(f"ProgrammingTask with task_id {task_id} not found.")
            
            task = self.db.query(Task).filter(Task.id == task_id).first()
            if not task:
                raise ValueError(f"Task with id {task_id} not found.")

            record.real_start_time = stopwatch.created_at
            record.real_end_time = now
            record.real_quantity = real_quantity
            record.duration_in_hours = accumulated_duration
            record.completed_by_user_id = user_id
            
            if record.real_quantity is not None and task.quantity is not None:
                record.is_completed = record.real_quantity >= task.quantity
            else:
                record.is_completed = False

        # Delete from stopwatch
        self.db.delete(stopwatch)

        self.db.commit()
        
        if record:
            self.db.refresh(record)

        return record

    def get_tasks_status(self, task_ids: list[uuid.UUID]):
        logger.info(f"get_tasks_status called for task_ids: {task_ids}")
        # Get tasks from Stopwatch (running, paused)
        stopwatch_tasks = self.db.query(Stopwatch.task_id, Stopwatch.status, Stopwatch.id, Stopwatch.is_from_programming).filter(
            Stopwatch.task_id.in_(task_ids),
            Stopwatch.is_from_programming == True
        ).all()
        logger.info(f"Stopwatch tasks found: {stopwatch_tasks}")

        # Get tasks from ProgrammingTask (completed/done, from programming)
        programming_completed_tasks = self.db.query(ProgrammingTask.task_id).filter(
            ProgrammingTask.task_id.in_(task_ids),
            ProgrammingTask.real_end_time.isnot(None)
        ).all()
        logger.info(f"Programming completed tasks found: {programming_completed_tasks}")

        # Create a dictionary to hold the status
        task_statuses = {}

        # Add running/paused tasks from Stopwatch
        for task_id, status, stopwatch_id, is_from_programming in stopwatch_tasks:
            task_statuses[str(task_id)] = {"status": status.value, "record_id": str(stopwatch_id), "is_from_programming": is_from_programming}

        # Add completed tasks from ProgrammingTask (is_from_programming = True)
        for task_id_prog_completed, in programming_completed_tasks:
            task_statuses[str(task_id_prog_completed)] = {"status": TimerStatus.STOPPED.value, "record_id": None, "is_from_programming": True}

        final_statuses = [{"task_id": task_id, "status": data["status"], "record_id": data["record_id"], "is_from_programming": data["is_from_programming"]} for task_id, data in task_statuses.items()]
        logger.info(f"Final statuses returned: {final_statuses}")
        return final_statuses

    def get_record_stopwatch_info(self, task_id: uuid.UUID):
        record = self.db.query(RecordStopwatch).filter(RecordStopwatch.task_id == task_id).first()
        if not record:
            return None
        return {
            "id": str(record.id),
            "task_id": str(record.task_id),
            "quantity": record.quantity,
            "accumulated_duration": record.accumulated_duration,
            "creation_date": record.creation_date
        }

    def get_daily_record_stopwatches(self):
        # Get current UTC datetime, adjust by 6 hours, then extract the date part
        current_datetime_adjusted = datetime.now(timezone.utc) - timedelta(hours=6)
        today = current_datetime_adjusted.date()
        
        daily_records_query = self.db.query(
            RecordStopwatch,
            Code.code,
            Task.description,
            Task.type,
            Task.activity,
            Task.people,
            Code.activity.label("code_activity"),
            Code.type.label("code_type")
        ).join(Task, RecordStopwatch.task_id == Task.id).join(Code, Task.code_id == Code.id).filter(
            func.date(RecordStopwatch.creation_date) == today
        ).all()

        result = []
        for record_stopwatch, task_code, task_description, task_type, task_activity, task_people, code_activity, code_type in daily_records_query:
            result.append({
                "id": record_stopwatch.id,
                "task_id": record_stopwatch.task_id,
                "quantity": record_stopwatch.quantity,
                "accumulated_duration": record_stopwatch.accumulated_duration,
                "creation_date": record_stopwatch.creation_date,
                "code_code": task_code,
                "task_description": task_description,
                "task_type": task_type or code_type,
                "task_activity": task_activity or code_activity,
                "task_people": task_people,
            })
        return result

    def get_all_record_stopwatches(self):
        all_records_query = self.db.query(
            RecordStopwatch,
            Code.code,
            Task.description,
            Task.type,
            Task.activity,
            Task.people,
            Code.activity.label("code_activity"),
            Code.type.label("code_type")
        ).join(Task, RecordStopwatch.task_id == Task.id).join(Code, Task.code_id == Code.id).all()

        result = []
        for record_stopwatch, task_code, task_description, task_type, task_activity, task_people, code_activity, code_type in all_records_query:
            result.append({
                "id": record_stopwatch.id,
                "task_id": record_stopwatch.task_id,
                "quantity": record_stopwatch.quantity,
                "accumulated_duration": record_stopwatch.accumulated_duration,
                "creation_date": record_stopwatch.creation_date,
                "code_code": task_code,
                "task_description": task_description,
                "task_type": task_type or code_type,
                "task_activity": task_activity or code_activity,
                "task_people": task_people,
            })
        return result

    def get_tasks_status_not_programmed(self, task_ids: list[uuid.UUID]):
        logger.info(f"get_tasks_status_not_programmed called for task_ids: {task_ids}")
        # Get tasks from Stopwatch (running, paused) for non-programming tasks
        stopwatch_tasks = self.db.query(Stopwatch.task_id, Stopwatch.status, Stopwatch.id, Stopwatch.is_from_programming).filter(
            Stopwatch.task_id.in_(task_ids),
            Stopwatch.is_from_programming == False
        ).all()
        logger.info(f"Stopwatch tasks found: {stopwatch_tasks}")

        # Get tasks from RecordStopwatch (completed/done, not from programming)
        record_stopwatch_tasks = self.db.query(RecordStopwatch.task_id).filter(RecordStopwatch.task_id.in_(task_ids)).all()
        logger.info(f"RecordStopwatch tasks found: {record_stopwatch_tasks}")

        # Create a dictionary to hold the status
        task_statuses = {}

        # Add running/paused tasks from Stopwatch
        for task_id, status, stopwatch_id, is_from_programming in stopwatch_tasks:
            task_statuses[str(task_id)] = {"status": status.value, "record_id": str(stopwatch_id), "is_from_programming": is_from_programming}

        # Add completed tasks from RecordStopwatch (is_from_programming = False)
        for task_id_record, in record_stopwatch_tasks:
            if str(task_id_record) not in task_statuses:
                task_statuses[str(task_id_record)] = {"status": TimerStatus.STOPPED.value, "record_id": None, "is_from_programming": False}

        final_statuses = [{"task_id": task_id, "status": data["status"], "record_id": data["record_id"], "is_from_programming": data["is_from_programming"]} for task_id, data in task_statuses.items()]
        logger.info(f"Final statuses returned: {final_statuses}")
        return final_statuses
