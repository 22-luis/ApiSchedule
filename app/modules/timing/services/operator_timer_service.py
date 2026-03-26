from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Optional
from app.modules.programming.models.task import Task
from app.modules.timing.models.stopwatch import Stopwatch
from app.modules.timing.models.record_stopwatch import RecordStopwatch
from app.modules.programming.models.programming import ProgrammingTask
from app.modules.codes.models.code import Code
from app.modules.timing.models.state import TimerStatus
from datetime import datetime, timezone, timedelta
import pytz
import uuid
import logging
import sys
from app.shared.utils.core.time_utils import TimeZoneUtils

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
        from app.modules.timing.repositories import timer_repository
        from app.modules.programming.repositories import task_repository
        
        task = task_repository.find_by_id(self.db, str(task_id))
        if not task:
            raise ValueError("Task not found")

        existing_stopwatch = timer_repository.find_stopwatch_by_task(self.db, task_id, is_from_programming)
        if existing_stopwatch:
            raise ValueError("Stopwatch already exists for this task with the same programming flag")

        if start_time is None:
            start_time = TimeZoneUtils.get_now()

        stopwatch = Stopwatch(
            task_id=task_id,
            status=TimerStatus.RUNNING,
            quantity=0, # Quantity will be set at stop
            accumulated_duration=0,
            is_from_programming=is_from_programming,
            created_at=start_time,
            real_start_time=start_time
        )
        return timer_repository.save_stopwatch(self.db, stopwatch)

    def pause_stopwatch(self, task_id: uuid.UUID):
        from app.modules.timing.repositories import timer_repository
        now = TimeZoneUtils.get_now()
        
        stopwatch = timer_repository.find_running_stopwatch(self.db, task_id)

        if not stopwatch:
            raise ValueError("No running stopwatch found for this task")

        last_start_time = (stopwatch.update_at or stopwatch.created_at)
        if last_start_time and last_start_time.tzinfo:
            last_start_time = last_start_time.replace(tzinfo=None)

        elapsed_time = (now - last_start_time).total_seconds() / 3600  # Convert to hours

        stopwatch.accumulated_duration += elapsed_time
        stopwatch.status = TimerStatus.PAUSED
        stopwatch.update_at = now

        return timer_repository.save_stopwatch(self.db, stopwatch)

    def resume_stopwatch(self, task_id: uuid.UUID):
        from app.modules.timing.repositories import timer_repository
        
        stopwatch = timer_repository.find_paused_stopwatch(self.db, task_id)

        if not stopwatch:
            raise ValueError("No paused stopwatch found for this task")

        now = TimeZoneUtils.get_now()
        stopwatch.status = TimerStatus.RUNNING
        stopwatch.update_at = now

        return timer_repository.save_stopwatch(self.db, stopwatch)

    def stop_stopwatch(self, task_id: uuid.UUID, real_quantity: float, user_id: uuid.UUID, is_completed: bool | None = None):
        from app.modules.timing.repositories import timer_repository
        from app.modules.programming.repositories import task_repository
        
        now = TimeZoneUtils.get_now()
        
        stopwatch = timer_repository.find_stopwatch_by_task_any_status(self.db, task_id)

        if not stopwatch:
            raise ValueError("No stopwatch found for this task")

        if stopwatch.status == TimerStatus.STOPPED:
            raise ValueError("Stopwatch is already stopped")

        accumulated_duration: float = float(stopwatch.accumulated_duration)

        if stopwatch.status == TimerStatus.RUNNING:
            last_start_time = (stopwatch.update_at or stopwatch.created_at)
            if last_start_time and last_start_time.tzinfo:
                last_start_time = last_start_time.replace(tzinfo=None)

            time_difference = now - last_start_time
            elapsed_time = time_difference.total_seconds() / 3600  # Convert to hours
            accumulated_duration += elapsed_time

        # Create a record in record_stopwatch (ALWAYS, for all types of tasks)
        accumulated_duration_value: float = accumulated_duration
        record_stopwatch = RecordStopwatch(
            task_id=task_id,
            quantity=real_quantity,
            accumulated_duration=accumulated_duration_value,
            creation_date=now, # Use the same 'now' for consistency
            real_start_time=stopwatch.real_start_time,
            real_end_time=now
        )
        timer_repository.save_record_stopwatch(self.db, record_stopwatch)

        record: Optional[RecordStopwatch | ProgrammingTask] = None
        
        if not stopwatch.is_from_programming:
            record = record_stopwatch
        else:
            prog_task = task_repository.find_programming_task_by_task_id(self.db, task_id)
            if not prog_task:
                raise ValueError(f"ProgrammingTask with task_id {task_id} not found.")

            record = prog_task
            task = task_repository.find_by_id(self.db, str(task_id))
            if not task:
                raise ValueError(f"Task with id {task_id} not found.")

            prog_task.real_start_time = stopwatch.real_start_time.replace(tzinfo=None) if stopwatch.real_start_time else None
            prog_task.real_end_time = now
            prog_task.real_quantity = real_quantity

            # Flush to ensure record_stopwatch is included in the sum
            self.db.flush()
            
            # Calculate total duration from all record_stopwatch entries for this task
            task_uuid = task_id if isinstance(task_id, uuid.UUID) else uuid.UUID(str(task_id))
            total_duration = self.db.query(func.sum(RecordStopwatch.accumulated_duration)).filter(
                RecordStopwatch.task_id == task_uuid
            ).scalar() or 0.0
            
            logger.info(f"Syncing duration for task {task_uuid}: calculated total_duration = {total_duration}")
            
            prog_task.duration_in_hours = total_duration
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
        timer_repository.delete_stopwatch(self.db, stopwatch)

        if record:
            self.db.refresh(record)

        return record

    def get_tasks_status(self, task_ids: list[uuid.UUID]):
        logger.info(f"get_tasks_status called for task_ids: {task_ids}")
        # Get tasks from Stopwatch (running, paused)
        stopwatch_tasks = self.db.query(
            Stopwatch.task_id, 
            Stopwatch.status, 
            Stopwatch.id, 
            Stopwatch.is_from_programming,
            Stopwatch.real_start_time,
            Stopwatch.real_end_time
        ).filter(
            Stopwatch.task_id.in_(task_ids),
            Stopwatch.is_from_programming == True
        ).all()
        logger.info(f"Stopwatch tasks found: {stopwatch_tasks}")

        # Get tasks from ProgrammingTask (completed/done, from programming)
        programming_completed_tasks = self.db.query(
            ProgrammingTask.task_id,
            ProgrammingTask.real_start_time,
            ProgrammingTask.real_end_time
        ).filter(
            ProgrammingTask.task_id.in_(task_ids),
            ProgrammingTask.real_end_time.isnot(None)
        ).all()
        logger.info(f"Programming completed tasks found: {programming_completed_tasks}")

        # Create a dictionary to hold the status
        task_statuses = {}

        # Add running/paused tasks from Stopwatch
        for task_id, status, stopwatch_id, is_from_programming, r_start, r_end in stopwatch_tasks:
            task_statuses[str(task_id)] = {
                "status": status.value, 
                "record_id": str(stopwatch_id), 
                "is_from_programming": is_from_programming,
                "real_start_time": r_start.replace(tzinfo=None) if r_start else None,
                "real_end_time": r_end.replace(tzinfo=None) if r_end else None
            }

        # Add completed tasks from ProgrammingTask (is_from_programming = True)
        for result in programming_completed_tasks:
            # result is a named tuple (task_id, real_start_time, real_end_time)
            task_id_prog_completed = result.task_id
            
            task_statuses[str(task_id_prog_completed)] = {
                "status": TimerStatus.STOPPED.value, 
                "record_id": None, 
                "is_from_programming": True,
                "real_start_time": result.real_start_time.replace(tzinfo=None) if result.real_start_time else None,
                "real_end_time": result.real_end_time.replace(tzinfo=None) if result.real_end_time else None
            }

        final_statuses = [{
            "task_id": task_id, 
            "status": data["status"], 
            "record_id": data["record_id"], 
            "is_from_programming": data["is_from_programming"],
            "real_start_time": data.get("real_start_time"),
            "real_end_time": data.get("real_end_time")
        } for task_id, data in task_statuses.items()]
        logger.info(f"Final statuses returned: {final_statuses}")
        return final_statuses

    def get_record_stopwatch_info(self, task_id: uuid.UUID):
        from app.modules.timing.repositories import timer_repository
        record = timer_repository.find_record_by_task(self.db, task_id)
        if not record:
            return None
        return {
            "id": str(record.id),
            "task_id": str(record.task_id),
            "quantity": record.quantity,
            "accumulated_duration": record.accumulated_duration,
            "creation_date": record.creation_date.isoformat() if record.creation_date else None,
            "comments": record.comments
        }

    @staticmethod
    def _convert_to_utc(dt):
        if dt is None:
            return None
        if dt.tzinfo is None:
            # Assume it's in El Salvador timezone
            el_salvador_tz = pytz.timezone('America/El_Salvador')
            localized = el_salvador_tz.localize(dt)
            return localized.astimezone(pytz.UTC).replace(tzinfo=None)
        else:
            return dt.astimezone(pytz.UTC).replace(tzinfo=None)

    @staticmethod
    def _format_record_stopwatch_result(query_results):
        result = []
        for record_stopwatch, task_code, task_description, task_type, task_activity, task_people, code_activity, code_type in query_results:
            result.append({
                "id": record_stopwatch.id,
                "task_id": record_stopwatch.task_id,
                "quantity": record_stopwatch.quantity,
                "accumulated_duration": record_stopwatch.accumulated_duration,
                "creation_date": record_stopwatch.creation_date.isoformat() if record_stopwatch.creation_date else None,
                "code_code": task_code,
                "task_description": task_description,
                "task_type": task_type or code_type,
                "task_activity": task_activity or code_activity,
                "task_people": task_people,
                "comments": record_stopwatch.comments,
            })
        return result

    def get_daily_record_stopwatches(self):
        from app.modules.timing.repositories import timer_repository
        # Get current local datetime, then extract the date part
        current_datetime_adjusted = TimeZoneUtils.get_now()
        today = current_datetime_adjusted.date()

        daily_records_query = timer_repository.find_daily_records_with_details(self.db, today)
        return self._format_record_stopwatch_result(daily_records_query)

    def get_all_record_stopwatches(self):
        from app.modules.timing.repositories import timer_repository
        all_records_query = timer_repository.find_all_records_with_details(self.db)
        return self._format_record_stopwatch_result(all_records_query)

    def get_tasks_status_not_programmed(self, task_ids: list[uuid.UUID]):
        from app.modules.timing.repositories import timer_repository
        logger.info(f"get_tasks_status_not_programmed called for task_ids: {task_ids}")
        # Get tasks from Stopwatch (running, paused) for non-programming tasks
        stopwatch_tasks = timer_repository.find_stopwatches_by_task_ids(self.db, task_ids, False)
        logger.info(f"Stopwatch tasks found: {stopwatch_tasks}")

        # Get tasks from RecordStopwatch (completed/done, not from programming)
        record_stopwatch_tasks = timer_repository.find_records_by_task_ids(self.db, task_ids)
        logger.info(f"RecordStopwatch tasks found: {record_stopwatch_tasks}")

        # Create a dictionary to hold the status
        task_statuses = {}

        # Add running/paused tasks from Stopwatch
        for sw in stopwatch_tasks:
            task_statuses[str(sw.task_id)] = {
                "status": sw.status.value, 
                "record_id": str(sw.id), 
                "is_from_programming": sw.is_from_programming,
                "real_start_time": sw.real_start_time.replace(tzinfo=None) if sw.real_start_time else None,
                "real_end_time": sw.real_end_time.replace(tzinfo=None) if sw.real_end_time else None
            }

        for rec in record_stopwatch_tasks:
            if str(rec.task_id) not in task_statuses:
                task_statuses[str(rec.task_id)] = {
                    "status": TimerStatus.STOPPED.value, 
                    "record_id": str(rec.id), 
                    "is_from_programming": False,
                    "real_start_time": rec.real_start_time.replace(tzinfo=None) if rec.real_start_time else None,
                    "real_end_time": rec.real_end_time.replace(tzinfo=None) if rec.real_end_time else None
                }

        final_statuses = [{
            "task_id": task_id, 
            "status": data["status"], 
            "record_id": data["record_id"], 
            "is_from_programming": data["is_from_programming"],
            "real_start_time": data.get("real_start_time"),
            "real_end_time": data.get("real_end_time")
        } for task_id, data in task_statuses.items()]
        logger.info(f"Final statuses returned: {final_statuses}")
        return final_statuses

    def add_comment_to_record(self, record_id: uuid.UUID, comment: str):
        from app.modules.timing.repositories import timer_repository
        record = timer_repository.find_record_by_id(self.db, record_id)
        if not record:
            raise ValueError("Record not found")

        record.comments = comment
        return timer_repository.save_record_stopwatch(self.db, record)
