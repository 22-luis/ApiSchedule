import traceback
import sys
from datetime import date, datetime, time
from pytz import timezone
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload
from uuid import UUID

from app.modules.programming.models.programming import Programming, ProgrammingTask
from app.modules.programming.models.task import Task
from app.modules.organization.models.team import Team, UserTeam
from app.modules.organization.models.user import User
from app.modules.organization.models.role import UserRole
from app.modules.programming.models.task_creation_notification import TaskCreationNotification
from app.modules.programming.schemas.task import TaskOut
from app.modules.organization.schemas.user import UserOut
from app.modules.timer.models.record_stopwatch import RecordStopwatch
from app.shared.utils.business.programming_availability import update_programming_availability
from app.modules.automation.services.utils.programming_utils import ProgrammingUtils
from app.modules.quality.models.test_record import TestRecord as Test
from fastapi import HTTPException

class ProgrammingService:
    @staticmethod
    def user_belongs_to_team(user: User, team_id: str) -> bool:
        return any(str(team.id) == str(team_id) for team in getattr(user, "teams", []))

    @staticmethod
    def list_programmings(db: Session, current_user: User):
        privileged_roles = (UserRole.ADMIN, UserRole.PLANNER, UserRole.SUPERVISOR, UserRole.TIMEKEEPER, UserRole.QC_COORDINATOR, UserRole.QC_ASSISTANT)
        if current_user.role in privileged_roles:
            programmings = db.query(Programming).all()
        else:
            team_ids = [team.id for team in getattr(current_user, "teams", [])]
            programmings = db.query(Programming).filter(Programming.team_id.in_(team_ids)).all()
            
        result = []
        for p in programmings:
            result.append({
                "id": p.id,
                "date": p.date,
                "team_id": p.team_id,
                "tasks": [t.id for t in p.tasks]
            })
        return result

    @staticmethod
    def get_by_team_date(db: Session, team_id: str, date_str: str, current_user: User):
        try:
            date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
            
            programming = db.query(Programming).options(
                joinedload(Programming.programming_tasks).joinedload(ProgrammingTask.task).joinedload(Task.code),
                joinedload(Programming.programming_tasks).joinedload(ProgrammingTask.task).joinedload(Task.created_by_user)
            ).filter_by(team_id=team_id, date=date_obj).first()

            privileged_roles = (UserRole.ADMIN, UserRole.PLANNER, UserRole.SUPERVISOR, UserRole.TIMEKEEPER, UserRole.QC_COORDINATOR, UserRole.QC_ASSISTANT)
            autho = current_user.role in privileged_roles or ProgrammingService.user_belongs_to_team(current_user, team_id)
            
            if not programming:
                if not autho:
                    raise HTTPException(status_code=403, detail="Not authorized")
                programming = Programming(date=date_obj, team_id=team_id)
                db.add(programming)
                db.commit()
                db.refresh(programming)
            else:
                if not autho:
                    raise HTTPException(status_code=403, detail="Not authorized")

            task_ids = [pt.task_id for pt in programming.programming_tasks if pt.task_id]
            real_minutes_map = {}
            if task_ids:
                real_records = db.query(
                    RecordStopwatch.task_id,
                    func.sum(RecordStopwatch.accumulated_duration * 60).label('total_minutes')
                ).filter(
                    RecordStopwatch.task_id.in_(task_ids)
                ).group_by(RecordStopwatch.task_id).all()
                real_minutes_map = {str(r.task_id).lower(): r.total_minutes for r in real_records}

            tasks = []
            for pt in sorted(programming.programming_tasks, key=lambda pt: pt.order):
                task_obj = pt.task
                if not task_obj: continue
                
                t = TaskOut.model_validate(task_obj, from_attributes=True).model_dump()
                t['type'] = task_obj.type
                t['start_time'] = pt.start_time
                t['end_time'] = pt.end_time
                t['order'] = pt.order
                t['real_start_time'] = getattr(pt, 'real_start_time', None)
                t['real_end_time'] = getattr(pt, 'real_end_time', None)
                t['real_quantity'] = getattr(pt, 'real_quantity', None)
                t['duration_in_hours'] = getattr(pt, 'duration_in_hours', 0)
                
                real_min = real_minutes_map.get(str(pt.task_id).lower(), (t['duration_in_hours'] or 0) * 60)
                if real_min == 0 and pt.real_start_time and pt.real_end_time:
                    delta = pt.real_end_time - pt.real_start_time
                    real_min = delta.total_seconds() / 60.0
                
                t['accumulated_real_minutes'] = real_min
                t['comment'] = getattr(pt, 'comment', None)
                t['created_at'] = getattr(pt, 'created_at', None)
                
                if task_obj.created_by_user:
                    t['created_by_user'] = UserOut.model_validate(task_obj.created_by_user, from_attributes=True).model_dump()
                else:
                    t['created_by_user'] = None
                t['is_completed'] = getattr(pt, 'is_completed', None)
                tasks.append(t)

            return {
                "id": programming.id,
                "date": programming.date,
                "team_id": str(programming.team_id) if not isinstance(programming.team_id, UUID) else programming.team_id,
                "tasks": tasks
            }
        except HTTPException:
            raise
        except Exception as e:
            traceback.print_exc()
            raise HTTPException(status_code=500, detail=str(e))

    @staticmethod
    def get_summary(db: Session, team_id: str, date_str: str, current_user: User):
        try:
            date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
            programming = db.query(Programming).options(
                joinedload(Programming.programming_tasks).joinedload(ProgrammingTask.task).joinedload(Task.code)
            ).filter_by(team_id=team_id, date=date_obj).first()

            if not programming:
                raise HTTPException(status_code=404, detail="Programming not found")

            privileged_roles = (UserRole.ADMIN, UserRole.PLANNER, UserRole.SUPERVISOR, UserRole.TIMEKEEPER, UserRole.QC_COORDINATOR, UserRole.QC_ASSISTANT)
            if current_user.role not in privileged_roles and not ProgrammingService.user_belongs_to_team(current_user, team_id):
                raise HTTPException(status_code=403, detail="Not authorized")

            lotes = [str(pt.task.lote) for pt in programming.programming_tasks if pt.task and pt.task.lote]
            quality_map = {}
            if lotes:
                lote_ints = []
                for l in set(lotes):
                    try: lote_ints.append(int(l))
                    except ValueError: continue
                if lote_ints:
                    tests = db.query(Test).filter(Test.lote.in_(lote_ints)).all()
                    quality_map = {(test.lote, test.code_id): test.status.value if hasattr(test.status, 'value') else str(test.status) for test in tests}

            tasks = []
            for pt in sorted(programming.programming_tasks, key=lambda pt: pt.order):
                task_obj = pt.task
                if not task_obj: continue
                code_str = task_obj.code.code if task_obj.code else task_obj.fabricationCode
                if not code_str: continue

                q_status = None
                try:
                    lote_int = int(task_obj.lote) if task_obj.lote else None
                    if lote_int is not None:
                        q_status = quality_map.get((lote_int, task_obj.code_id))
                        if q_status is None:
                            q_status = quality_map.get((lote_int, None))
                except (ValueError, TypeError): pass

                tasks.append({
                    "lote": task_obj.lote,
                    "code": code_str,
                    "description": task_obj.description or (task_obj.code.description if task_obj.code else None),
                    "quality_status": q_status
                })

            return {
                "id": programming.id,
                "date": programming.date,
                "team_id": programming.team_id,
                "tasks": tasks
            }
        except HTTPException: raise
        except Exception as e:
            traceback.print_exc()
            raise HTTPException(status_code=500, detail=str(e))
    @staticmethod
    def get_dashboard_data(db: Session, date_str: str, current_user: User):
        """
        Retrieves dashboard data for a specific date, optimized to avoid N+1 queries.
        """
        try:
            # Convertir date a objeto date
            date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
            
            # Determinar qué programaciones puede ver el usuario
            privileged_roles = (UserRole.ADMIN, UserRole.PLANNER, UserRole.SUPERVISOR, UserRole.TIMEKEEPER, UserRole.QC_COORDINATOR, UserRole.QC_ASSISTANT)
            if current_user.role in privileged_roles:
                programmings_query = db.query(Programming)
            else:
                team_ids = [team.id for team in getattr(current_user, "teams", [])]
                programmings_query = db.query(Programming).filter(Programming.team_id.in_(team_ids))
            
            # Optimización: Cargar todas las programaciones de la fecha con eager loading
            programmings = programmings_query.options(
                joinedload(Programming.team).joinedload(Team.supervisor),
                joinedload(Programming.team).joinedload(Team.member_associations).joinedload(UserTeam.user),
                joinedload(Programming.programming_tasks).joinedload(ProgrammingTask.task).joinedload(Task.code),
                joinedload(Programming.programming_tasks).joinedload(ProgrammingTask.task).joinedload(Task.created_by_user)
            ).filter(
                Programming.date == date_obj
            ).all()
            
            # Construir la respuesta con todos los datos
            result = []
            for programming in programmings:
                # Solo incluir programaciones que tienen tareas
                if not programming.programming_tasks:
                    continue
                    
                # Obtener minutos reales acumulados de RecordStopwatch para esta programación
                task_ids = [pt.task_id for pt in programming.programming_tasks if pt.task_id]
                real_minutes_map = {}
                if task_ids:
                    real_records = db.query(
                        RecordStopwatch.task_id,
                        func.sum(RecordStopwatch.accumulated_duration * 60).label('total_minutes')
                    ).filter(
                        RecordStopwatch.task_id.in_(task_ids)
                    ).group_by(RecordStopwatch.task_id).all()
                    real_minutes_map = {str(r.task_id).lower(): r.total_minutes for r in real_records}

                # Serializar las tareas
                tasks = []
                for pt in sorted(programming.programming_tasks, key=lambda pt: pt.order):
                    task_obj = pt.task
                    if not task_obj:
                        continue
                        
                    t = TaskOut.model_validate(task_obj, from_attributes=True).model_dump()
                    t['type'] = task_obj.type
                    t['start_time'] = pt.start_time
                    t['end_time'] = pt.end_time
                    t['order'] = pt.order
                    t['real_start_time'] = getattr(pt, 'real_start_time', None)
                    t['real_end_time'] = getattr(pt, 'real_end_time', None)
                    t['real_quantity'] = getattr(pt, 'real_quantity', None)
                    t['duration_in_hours'] = getattr(pt, 'duration_in_hours', 0)
                    
                    # Multi-level fallback for accumulated_real_minutes
                    real_min = real_minutes_map.get(str(pt.task_id).lower(), (t['duration_in_hours'] or 0) * 60)
                    
                    # Final fallback to timestamps if the others are missing/zero
                    if real_min == 0 and pt.real_start_time and pt.real_end_time:
                        delta = pt.real_end_time - pt.real_start_time
                        real_min = delta.total_seconds() / 60.0
                    
                    t['accumulated_real_minutes'] = real_min
                    t['comment'] = getattr(pt, 'comment', None)
                    t['created_at'] = getattr(pt, 'created_at', None)
                    
                    # Serializar created_by_user
                    if task_obj.created_by_user:
                        t['created_by_user'] = UserOut.model_validate(task_obj.created_by_user, from_attributes=True).model_dump()
                    else:
                        t['created_by_user'] = None
                        
                    t['is_completed'] = getattr(pt, 'is_completed', None)
                    tasks.append(t)
                
                # Serializar el equipo
                team_data = None
                if programming.team:
                    team_data = {
                        "id": str(programming.team.id),
                        "name": programming.team.name,
                        "description": getattr(programming.team, 'description', None),
                        "supervisorUsername": programming.team.supervisor.username if programming.team.supervisor else None,
                        "members": programming.team.members
                    }
                
                # Agregar al resultado
                result.append({
                    "team": team_data,
                    "programming": {
                        "id": programming.id,
                        "date": programming.date,
                        "team_id": str(programming.team_id) if not isinstance(programming.team_id, UUID) else programming.team_id,
                        "tasks": tasks
                    }
                })
            
            return {
                "date": date_obj,
                "team_programmings": result,
                "count": len(result)
            }
        except Exception as e:
            print("[DEBUG] Exception in get_dashboard_data service:", e)
            traceback.print_exc()
            raise

    @staticmethod
    def reorder_programming_tasks(db: Session, programming_id: UUID, tasks_order_data):
        """
        Reorders tasks within a programming and recalculates their scheduled times.
        """
        programming = db.query(Programming).get(programming_id)
        if not programming:
            return None, "Programming not found"
        
        programming_tasks_map = {pt.task_id: pt for pt in programming.programming_tasks}
        result = []
        current_time = None
        sv_tz = timezone("America/El_Salvador")
        
        # In sorted order based on requested sequence
        for item in sorted(tasks_order_data, key=lambda x: x.order):
            pt = programming_tasks_map.get(item.task_id)
            if not pt:
                return None, f"Task {item.task_id} not found in programming"
            
            pt.order = item.order
            pt.duration_in_hours = item.duration_in_hours
            
            # Use explicit times if provided, otherwise calculate
            if item.start_time and item.end_time:
                st = item.start_time if isinstance(item.start_time, datetime) else datetime.fromisoformat(item.start_time)
                et = item.end_time if isinstance(item.end_time, datetime) else datetime.fromisoformat(item.end_time)
                
                # Normalize to America/El_Salvador if it has TZ info
                if st.tzinfo:
                    st = st.astimezone(sv_tz).replace(tzinfo=None)
                if et.tzinfo:
                    et = et.astimezone(sv_tz).replace(tzinfo=None)
                    
                pt.start_time = st
                pt.end_time = et
                current_time = pt.end_time
            else:
                programming_date: date = programming.date
                weekday = programming_date.weekday()
                if current_time is None:
                    # Starting time of the day
                    if weekday == 5: # Saturday
                        current_time = datetime.combine(programming_date, time(7, 30))
                    else:
                        current_time = datetime.combine(programming_date, time(7, 0))
                
                # Adjust start if it falls during lunch break
                curr_mins = current_time.hour * 60 + current_time.minute
                if 720 <= curr_mins < 780:
                    current_time = datetime.combine(programming_date, time(13, 0))
                
                pt.start_time = current_time
                duration = getattr(pt.task, "minutes", 0) or 0
                
                # Calculate end time using lunch break adjustment utility
                pt.end_time = ProgrammingUtils.adjust_for_lunch_break(current_time, duration)
                current_time = pt.end_time
                
            result.append({
                "task_id": pt.task_id,
                "order": pt.order,
                "start_time": pt.start_time,
                "end_time": pt.end_time,
                "duration_in_hours": pt.duration_in_hours
            })
            
        db.commit()
        
        # Update programming availability after reordering
        update_programming_availability(db, programming)
        
        return result, None

    @staticmethod
    def get_recent_task_creation_notifications(db: Session):
        from datetime import timedelta
        cutoff_time = datetime.utcnow() - timedelta(hours=24)
        notifications = db.query(TaskCreationNotification).filter(
            TaskCreationNotification.created_at >= cutoff_time
        ).order_by(
            TaskCreationNotification.created_at.desc()
        ).all()
        
        serialized = []
        for n in notifications:
            serialized.append({
                "id": str(n.id),
                "created_at": n.created_at.isoformat(),
                "created_by": n.created_by,
                "programming_info": n.programming_info,
                "order_count": n.order_count
            })
        return serialized
