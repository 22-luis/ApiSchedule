from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Optional
from app.modules.programming.models.task import Task
from app.modules.timer.models.stopwatch import Stopwatch
from app.modules.timer.models.record_stopwatch import RecordStopwatch
from app.modules.programming.models.programming import ProgrammingTask
from app.modules.codes.models.code import Code
from app.modules.timer.models.state import TimerStatus
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

    def stop_stopwatch(self, task_id: uuid.UUID, real_quantity: float, user_id: uuid.UUID, is_completed: bool | None = None):
        now = datetime.now(timezone.utc) - timedelta(hours=6)
        
        stopwatch = self.db.query(Stopwatch).filter(Stopwatch.task_id == task_id).first()

        if not stopwatch:
            raise ValueError("No stopwatch found for this task")

        if stopwatch.status == TimerStatus.STOPPED:
            raise ValueError("Stopwatch is already stopped")

        accumulated_duration: float = float(stopwatch.accumulated_duration)

        if stopwatch.status == TimerStatus.RUNNING:
            last_start_time = (stopwatch.update_at or stopwatch.created_at).astimezone(timezone.utc)
            time_difference = now - last_start_time
            elapsed_time = time_difference.total_seconds() / 3600  # Convert to hours
            accumulated_duration += elapsed_time

        _record: Optional[RecordStopwatch | ProgrammingTask] = None
        # Create a record in record_stopwatch or update ProgrammingTask
        if not stopwatch.is_from_programming:
            accumulated_duration_value: float = accumulated_duration
            record = RecordStopwatch(
                task_id=task_id,
                quantity=real_quantity,
                accumulated_duration=accumulated_duration_value
            )
            self.db.add(record)
        else:
            prog_task: Optional[ProgrammingTask] = self.db.query(ProgrammingTask).filter(ProgrammingTask.task_id == task_id).first()
            if not prog_task:
                raise ValueError(f"ProgrammingTask with task_id {task_id} not found.")

            record = prog_task
            task: Optional[Task] = self.db.query(Task).filter(Task.id == task_id).first()
            if not task:
                raise ValueError(f"Task with id {task_id} not found.")

            prog_task.real_start_time = stopwatch.created_at
            prog_task.real_end_time = now
            prog_task.real_quantity = real_quantity
            prog_task.duration_in_hours = accumulated_duration
            prog_task.completed_by_user_id = user_id

            if is_completed is not None:
                prog_task.is_completed = is_completed
            elif prog_task.real_quantity is not None and task.quantity is not None:
                prog_task.is_completed = prog_task.real_quantity >= task.quantity
            else:
                prog_task.is_completed = False

            # IMPORTANT: Update order status and fabricated_quantity
            from app.shared.utils.business.order_status_service import OrderStatusService
            try:
                OrderStatusService.update_order_status_for_task_completion(self.db, prog_task)
                logger.info(f"Order status updated for task {task_id}")
            except Exception as e:
                logger.error(f"Error updating order status for task {task_id}: {e}")

        # Delete it from the stopwatch
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
        for result in programming_completed_tasks:
            # the result is a Row object or a tuple depending on sqlalchemy version/query style.
            # Since we only queried one column, it might be a single value or a tuple with one element.
            # safely accessing task_id
            task_id_prog_completed = result.task_id if hasattr(result, 'task_id') else result[0]
            
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
            "creation_date": record.creation_date,
            "comments": record.comments
        }

    @staticmethod
    def _format_record_stopwatch_result(query_results):
        result = []
        for record_stopwatch, task_code, task_description, task_type, task_activity, task_people, code_activity, code_type in query_results:
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
                "comments": record_stopwatch.comments,
            })
        return result

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

        return self._format_record_stopwatch_result(daily_records_query)

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

        return self._format_record_stopwatch_result(all_records_query)

    def get_tasks_status_not_programmed(self, task_ids: list[uuid.UUID]):
        logger.info(f"get_tasks_status_not_programmed called for task_ids: {task_ids}")
        # Get tasks from Stopwatch (running, paused) for non-programming tasks
        stopwatch_tasks = self.db.query(Stopwatch.task_id, Stopwatch.status, Stopwatch.id, Stopwatch.is_from_programming).filter(
            Stopwatch.task_id.in_(task_ids),
            Stopwatch.is_from_programming == False
        ).all()
        logger.info(f"Stopwatch tasks found: {stopwatch_tasks}")

        # Get tasks from RecordStopwatch (completed/done, not from programming)
        record_stopwatch_tasks = self.db.query(RecordStopwatch.task_id, RecordStopwatch.id).filter(RecordStopwatch.task_id.in_(task_ids)).all()
        logger.info(f"RecordStopwatch tasks found: {record_stopwatch_tasks}")

        # Create a dictionary to hold the status
        task_statuses = {}

        # Add running/paused tasks from Stopwatch
        for task_id, status, stopwatch_id, is_from_programming in stopwatch_tasks:
            task_statuses[str(task_id)] = {"status": status.value, "record_id": str(stopwatch_id), "is_from_programming": is_from_programming}

        for task_id_record, record_id in record_stopwatch_tasks:
            if str(task_id_record) not in task_statuses:
                task_statuses[str(task_id_record)] = {"status": TimerStatus.STOPPED.value, "record_id": str(record_id), "is_from_programming": False}

        final_statuses = [{"task_id": task_id, "status": data["status"], "record_id": data["record_id"], "is_from_programming": data["is_from_programming"]} for task_id, data in task_statuses.items()]
        logger.info(f"Final statuses returned: {final_statuses}")
        return final_statuses

    def add_comment_to_record(self, record_id: uuid.UUID, comment: str):
        record = self.db.query(RecordStopwatch).filter(RecordStopwatch.id == record_id).first()
        if not record:
            raise ValueError("Record not found")

        record.comments = comment
        self.db.commit()
        self.db.refresh(record)
        return record
