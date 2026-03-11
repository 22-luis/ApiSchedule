import datetime
from typing import List, Dict, Any, Optional, cast
from sqlalchemy.orm import Session, joinedload
from fastapi import HTTPException
from pytz import timezone

from app.modules.programming.models.task import Task
from app.modules.organization.models.team import Team, task_team_association
from app.modules.organization.models.user import User
from app.modules.organization.models.role import UserRole
from app.modules.programming.models.programming import Programming, ProgrammingTask
from app.modules.programming.models.task_status_log import TaskStatusLog
from app.shared.core.enums import TaskStatus
from app.modules.programming.schemas.task_status_log import TaskStatusLogCreate
from app.shared.utils.business.order_status_service import OrderStatusService
from app.shared.utils.business.programming_availability import update_programming_availability_by_task, restore_programmings_availability
from app.modules.automation.services.replicate_pesado import replicate_task_to_pesado_if_needed

class TaskService:
    @staticmethod
    def get_task_with_relations(db: Session, task_id: str) -> Optional[Task]:
        return db.query(Task).options(
            joinedload(Task.code),
            joinedload(Task.preparation),
            joinedload(Task.teams),
            joinedload(Task.created_by_user)
        ).filter(Task.id == task_id).first()

    @staticmethod
    def check_user_team_permission(current_user: User, programming: Programming):
        if current_user.role == UserRole.USER:
            user_team_ids = {str(team.id) for team in current_user.teams}
            if str(programming.team_id) not in user_team_ids:
                raise HTTPException(status_code=403, detail="You can only create tasks for your assigned teams")

    @staticmethod
    def create_task(db: Session, task_data: Dict[str, Any], team_ids: List[str], programming_id: str, current_user: User) -> Task:
        programming = db.query(Programming).filter(Programming.id == programming_id).first()
        if not programming:
            raise HTTPException(status_code=404, detail="Programming not found")

        TaskService.check_user_team_permission(current_user, programming)

        teams = db.query(Team).filter(Team.id.in_(team_ids)).all()
        if len(teams) != len(team_ids):
            raise HTTPException(status_code=400, detail="One or more teams not found")

        # Create Task
        db_task = Task(
            **task_data,
            teams=teams,
            created_by_user_id=current_user.id
        )
        db.add(db_task)
        db.flush()

        # Associate with Programming
        max_order = db.query(ProgrammingTask).filter(ProgrammingTask.programming_id == programming.id).count()
        sv_tz = timezone("America/El_Salvador")
        st, et = db_task.start_time, db_task.end_time
        
        if st and st.tzinfo:
            st = st.astimezone(sv_tz).replace(tzinfo=None)
        if et and et.tzinfo:
            et = et.astimezone(sv_tz).replace(tzinfo=None)

        programming_task = ProgrammingTask(
            programming_id=programming.id,
            task_id=db_task.id,
            order=max_order + 1,
            start_time=st,
            end_time=et
        )
        db.add(programming_task)

        # Side effects
        OrderStatusService.update_order_status_for_task_creation(db, db_task)
        db.commit()

        if current_user.role in [UserRole.ADMIN, UserRole.PLANNER, UserRole.SUPERVISOR]:
            replicate_task_to_pesado_if_needed(db, db_task, programming.date)

        update_programming_availability_by_task(db, str(db_task.id))
        
        return TaskService.get_task_with_relations(db, str(db_task.id))

    @staticmethod
    def duplicate_task(db: Session, task_id: str, new_lote: str, current_user: User) -> Task:
        original_task = TaskService.get_task_with_relations(db, task_id)
        if not original_task:
            raise HTTPException(status_code=404, detail="Original task not found")

        programming = db.query(Programming).join(ProgrammingTask).filter(ProgrammingTask.task_id == task_id).first()
        if not programming:
            raise HTTPException(status_code=404, detail="Task not associated with any programming")

        TaskService.check_user_team_permission(current_user, programming)

        task_data = {
            field: getattr(original_task, field) for field in Task.__table__.columns.keys()
            if field not in ['id', 'created_at', 'updated_at', 'created_by_user_id', 'status', 'is_completed']
        }
        task_data['lote'] = new_lote
        task_data['status'] = TaskStatus.PENDING.value
        task_data['is_completed'] = False

        team_ids = [str(team.id) for team in original_task.teams]
        
        return TaskService.create_task(db, task_data, team_ids, str(programming.id), current_user)

    @staticmethod
    def update_task(db: Session, task_id: str, update_data: Dict[str, Any], current_user: User) -> Task:
        db_task = db.query(Task).filter(Task.id == task_id).first()
        if not db_task:
            raise HTTPException(status_code=404, detail="Task not found")
        
        team_ids = update_data.pop("teamIds", None)
        updating_times = 'start_time' in update_data or 'end_time' in update_data
        
        for field, value in update_data.items():
            setattr(db_task, field, value)
            
        if team_ids is not None:
            teams = db.query(Team).filter(Team.id.in_(team_ids)).all()
            if len(teams) != len(team_ids):
                raise HTTPException(status_code=400, detail="One or more teams not found")
            db_task.teams = teams
        
        if updating_times:
            sv_tz = timezone("America/El_Salvador")
            programming_tasks = db.query(ProgrammingTask).filter(ProgrammingTask.task_id == task_id).all()
            for pt in programming_tasks:
                if 'start_time' in update_data:
                    st = update_data['start_time']
                    if st and hasattr(st, 'tzinfo') and st.tzinfo:
                        st = st.astimezone(sv_tz).replace(tzinfo=None)
                    pt.start_time = st
                if 'end_time' in update_data:
                    et = update_data['end_time']
                    if et and hasattr(et, 'tzinfo') and et.tzinfo:
                        et = et.astimezone(sv_tz).replace(tzinfo=None)
                    pt.end_time = et
        
        db.commit()
        if updating_times:
            update_programming_availability_by_task(db, task_id)
            
        return TaskService.get_task_with_relations(db, task_id)

    @staticmethod
    def update_task_status(db: Session, task_id: str, new_status: TaskStatus, current_user: User) -> Task:
        db_task = TaskService.get_task_with_relations(db, task_id)
        if not db_task:
            raise HTTPException(status_code=404, detail="Task not found")

        if db_task.is_completed:
            raise HTTPException(status_code=400, detail="Cannot change status of a completed task")

        if new_status.value == db_task.status:
            return db_task

        # Auth check for pausing
        if new_status == TaskStatus.PAUSED and current_user.role == UserRole.USER:
            # Replicating existing logic from routes_task.py
            allowed_task_types = ["M1", "M12", "M13", "M15"]
            if db_task.type not in allowed_task_types:
                raise HTTPException(status_code=403, detail="You are not authorized to pause this type of task")

        now = datetime.datetime.utcnow()
        current_log_entry = db.query(TaskStatusLog).filter(
            TaskStatusLog.task_id == db_task.id,
            TaskStatusLog.end_time == None
        ).first()

        if current_log_entry:
            current_log_entry.end_time = now

        new_log_entry = TaskStatusLog(task_id=db_task.id, status=new_status.value, start_time=now)
        db.add(new_log_entry)
        db_task.status = new_status.value
        db.commit()
        db.refresh(db_task)
        return db_task

    @staticmethod
    def change_task_status(db: Session, task_id: str, new_status_val: str) -> TaskStatusLog:
        from app.modules.programming.models.task import Task
        task = db.query(Task).filter(Task.id == task_id).first()
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")

        latest_log = db.query(TaskStatusLog).filter(TaskStatusLog.task_id == task_id).order_by(TaskStatusLog.start_time.desc()).first()

        if latest_log:
            if latest_log.status == new_status_val:
                return latest_log
            latest_log.end_time = datetime.datetime.utcnow()
            db.add(latest_log)

        new_log = TaskStatusLog(
            task_id=task_id,
            status=new_status_val,
            start_time=datetime.datetime.utcnow()
        )
        db.add(new_log)
        task.status = new_status_val
        db.add(task)
        db.commit()
        db.refresh(new_log)
        return new_log

    @staticmethod
    def get_status_logs(db: Session, task_id: str) -> List[TaskStatusLog]:
        return db.query(TaskStatusLog).filter(TaskStatusLog.task_id == task_id).order_by(TaskStatusLog.start_time.asc()).all()

    @staticmethod
    def delete_tasks(db: Session, task_ids: List[str]) -> bool:
        tasks_to_delete = db.query(Task).filter(Task.id.in_(task_ids)).all()
        if len(tasks_to_delete) != len(set(task_ids)):
            return False

        try:
            for task in tasks_to_delete:
                OrderStatusService.update_order_status_for_task_deletion(db, task)
                update_programming_availability_by_task(db, str(task.id))
                db.execute(task_team_association.delete().where(task_team_association.c.task_id == task.id))
                db.delete(task)
            db.commit()
            restore_programmings_availability(db)
            return True
        except Exception:
            db.rollback()
            raise
