import traceback
import sys
from typing import List, Optional
from datetime import date, datetime, time
from pytz import timezone
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload
from uuid import UUID

from app.modules.programming.models.programming import Programming, ProgrammingTask
from app.modules.programming.models.task import Task
from app.modules.programming.models.state import ProgrammingStatus
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
    def list_programmings(db: Session, current_user: User, date_str: Optional[str] = None):
        from app.modules.programming.repositories import programming_repository
        privileged_roles = (UserRole.ADMIN, UserRole.PLANNER, UserRole.SUPERVISOR, UserRole.TIMEKEEPER, UserRole.QC_COORDINATOR, UserRole.QC_ASSISTANT)
        
        if date_str:
            try:
                date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
                if current_user.role in privileged_roles:
                    programmings = db.query(Programming).filter(Programming.date == date_obj).all()
                else:
                    team_ids = [team.id for team in getattr(current_user, "teams", [])]
                    programmings = db.query(Programming).filter(
                        Programming.team_id.in_(team_ids),
                        Programming.date == date_obj
                    ).all()
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid date format")
        else:
            if current_user.role in privileged_roles:
                programmings = programming_repository.find_all(db)
            else:
                team_ids = [team.id for team in getattr(current_user, "teams", [])]
                programmings = programming_repository.find_by_team_ids(db, team_ids)
            
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
        from app.modules.programming.repositories import programming_repository
        try:
            date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
            
            programming = programming_repository.find_by_team_and_date(db, team_id, date_obj)

            privileged_roles = (UserRole.ADMIN, UserRole.PLANNER, UserRole.SUPERVISOR, UserRole.TIMEKEEPER, UserRole.QC_COORDINATOR, UserRole.QC_ASSISTANT)
            autho = current_user.role in privileged_roles or ProgrammingService.user_belongs_to_team(current_user, team_id)
            
            if not programming:
                if not autho:
                    raise HTTPException(status_code=403, detail="Not authorized")
                programming = Programming(date=date_obj, team_id=team_id)
                programming = programming_repository.save(db, programming)
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
            
            # Optimización: Cargar todas las programaciones de la fecha con eager loading completo
            programmings = programmings_query.options(
                joinedload(Programming.team).joinedload(Team.supervisor),
                joinedload(Programming.team).joinedload(Team.member_associations).joinedload(UserTeam.user),
                joinedload(Programming.programming_tasks).joinedload(ProgrammingTask.task).joinedload(Task.code),
                joinedload(Programming.programming_tasks).joinedload(ProgrammingTask.task).joinedload(Task.teams),
                joinedload(Programming.programming_tasks).joinedload(ProgrammingTask.task).joinedload(Task.created_by_user)
            ).filter(
                Programming.date == date_obj
            ).all()
            
            # Optimización: Obtener TODOS los minutos reales para TODAS las tareas de la fecha en UNA SOLA consulta
            all_task_ids = []
            for p in programmings:
                all_task_ids.extend([pt.task_id for pt in p.programming_tasks if pt.task_id])
            
            global_real_minutes_map = {}
            if all_task_ids:
                real_records = db.query(
                    RecordStopwatch.task_id,
                    func.sum(RecordStopwatch.accumulated_duration * 60).label('total_minutes')
                ).filter(
                    RecordStopwatch.task_id.in_(all_task_ids)
                ).group_by(RecordStopwatch.task_id).all()
                global_real_minutes_map = {str(r.task_id).lower(): r.total_minutes for r in real_records}

            # Optimización: Obtener estados de supervisión para todas las tareas
            global_sup_status_map = {}
            if all_task_ids:
                from app.modules.supervisor.models.sup_stopwatch import SupStopwatch
                from app.modules.supervisor.models.sup_record_stopwatch import SupRecordStopwatch
                
                # Buscar temporizadores activos
                active_sup = db.query(SupStopwatch.task_id, SupStopwatch.status).filter(
                    SupStopwatch.task_id.in_(all_task_ids)
                ).all()
                for r in active_sup:
                    global_sup_status_map[str(r.task_id).lower()] = r.status.value if hasattr(r.status, 'value') else str(r.status)
                
                # Buscar registros históricos (para tareas que no están activas)
                # Si una tarea tiene un registro histórico y NO está activa, se considera 'stopped' (Revisada)
                stopped_sup = db.query(SupRecordStopwatch.task_id).filter(
                    SupRecordStopwatch.task_id.in_(all_task_ids)
                ).distinct().all()
                for r in stopped_sup:
                    tid = str(r.task_id).lower()
                    if tid not in global_sup_status_map:
                        global_sup_status_map[tid] = 'stopped'

            # Construir la respuesta con todos los datos
            result = []
            for programming in programmings:
                if not programming.programming_tasks:
                    continue
                    
                # Serializar las tareas usando el mapa global de minutos y supervisión
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
                    
                    real_min = global_real_minutes_map.get(str(pt.task_id).lower(), (t['duration_in_hours'] or 0) * 60)
                    
                    if real_min == 0 and pt.real_start_time and pt.real_end_time:
                        delta = pt.real_end_time - pt.real_start_time
                        real_min = delta.total_seconds() / 60.0
                    
                    t['accumulated_real_minutes'] = real_min
                    t['comment'] = getattr(pt, 'comment', None)
                    t['created_at'] = getattr(pt, 'created_at', None)
                    
                    # Agregar estado de supervisión
                    t['sup_status'] = global_sup_status_map.get(str(pt.task_id).lower(), 'pending')
                    
                    if task_obj.created_by_user:
                        t['created_by_user'] = UserOut.model_validate(task_obj.created_by_user, from_attributes=True).model_dump()
                    else:
                        t['created_by_user'] = None
                        
                    t['is_completed'] = getattr(pt, 'is_completed', None)
                    tasks.append(t)
                
                team_data = None
                if programming.team:
                    team_data = {
                        "id": str(programming.team.id),
                        "name": programming.team.name,
                        "description": getattr(programming.team, 'description', None),
                        "supervisorUsername": programming.team.supervisor.username if programming.team.supervisor else None,
                        "members": programming.team.members
                    }
                
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
    def update_task_real_quantity(db: Session, programming_id: UUID, task_id: UUID, real_quantity: float):
        from app.modules.programming.repositories import task_repository
        pt = task_repository.find_programming_task(db, programming_id, task_id)
        if not pt:
            raise HTTPException(status_code=404, detail="Task not found in this programming")
        
        pt.real_quantity = real_quantity
        task_repository.commit(db)
        db.refresh(pt)
        return pt

    @staticmethod
    def update_task_comment(db: Session, programming_id: UUID, task_id: UUID, comment: str):
        from app.modules.programming.repositories import task_repository
        pt = task_repository.find_programming_task(db, programming_id, task_id)
        if not pt:
            raise HTTPException(status_code=404, detail="Task not found in this programming")
        
        pt.comment = comment
        task_repository.commit(db)
        db.refresh(pt)
        return pt

    @staticmethod
    def toggle_task_status(db: Session, programming_id: UUID, task_id: UUID, payload: dict, current_user: User):
        from app.modules.programming.services.task_timer_service import TaskTimerService
        from app.modules.programming.repositories import task_repository
        
        pt = task_repository.find_programming_task(db, programming_id, task_id)
        if not pt:
            raise HTTPException(status_code=404, detail="Task not found in this programming")
            
        task = pt.task
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")

        # Update quantities if provided
        if "assigned_quantity" in payload and payload["assigned_quantity"] is not None:
            task.quantity = payload["assigned_quantity"]
        
        if "real_quantity" in payload and payload["real_quantity"] is not None:
            pt.real_quantity = payload["real_quantity"]

        # Toggle completion status
        is_completed = pt.is_completed if pt.is_completed is not None else False
        new_status = not is_completed
        pt.is_completed = new_status
        
        if new_status:
            # Complements status update in Task model
            from app.shared.core.enums import TaskStatus as SharedTaskStatus
            task.status = SharedTaskStatus.COMPLETED.value
            task.is_completed = True
            
            # If it was in progress, stop the timer
            from app.modules.programming.schemas.programming import ProgrammingTaskReportIn
            from app.modules.programming.services.task_timer_service import TaskTimerService
            report_data = ProgrammingTaskReportIn(real_quantity=pt.real_quantity)
            TaskTimerService.stop_timer(db=db, task_id=str(task_id), current_user=current_user, data=report_data, programming_id=str(programming_id))
        else:
            from app.shared.core.enums import TaskStatus as SharedTaskStatus
            task.status = SharedTaskStatus.PENDING.value
            task.is_completed = False
            
        task_repository.commit(db)
        db.refresh(pt)
        db.refresh(task)
        print(f"DEBUG - success toggle")
        
        return pt

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

    @staticmethod
    def get_monthly_performance(db: Session, year: int, month: int, current_user: User):
        """
        Calculates monthly performance summary for all teams.
        Optimized to handle a full month of data in a single call.
        """
        # 1. Definir rango del mes
        start_date = date(year, month, 1)
        if month == 12:
            end_date = date(year + 1, 1, 1)
        else:
            end_date = date(year, month + 1, 1)
            
        # 2. Obtener todas las programaciones del mes con sus tareas
        privileged_roles = (UserRole.ADMIN, UserRole.PLANNER, UserRole.SUPERVISOR, UserRole.TIMEKEEPER, UserRole.QC_COORDINATOR, UserRole.QC_ASSISTANT)
        
        query = db.query(Programming).options(
            joinedload(Programming.team),
            joinedload(Programming.programming_tasks).joinedload(ProgrammingTask.task).joinedload(Task.code)
        ).filter(
            Programming.date >= start_date,
            Programming.date < end_date
        )
        
        if current_user.role not in privileged_roles:
            team_ids = [team.id for team in getattr(current_user, "teams", [])]
            query = query.filter(Programming.team_id.in_(team_ids))
            
        programmings = query.all()
        
        # 3. Obtener minutos reales masivos para todas las tareas del mes
        all_task_ids = []
        for p in programmings:
            all_task_ids.extend([pt.task_id for pt in p.programming_tasks if pt.task_id])
            
        real_minutes_map = {}
        if all_task_ids:
            real_records = db.query(
                RecordStopwatch.task_id,
                func.sum(RecordStopwatch.accumulated_duration * 60).label('total_minutes')
            ).filter(
                RecordStopwatch.task_id.in_(all_task_ids)
            ).group_by(RecordStopwatch.task_id).all()
            real_minutes_map = {str(r.task_id).lower(): r.total_minutes for r in real_records}
            
        # 4. Procesar y agrupar por equipo y fecha
        # perf_matrix: { team_id: { date: performance } }
        perf_matrix = {}
        active_days = set()
        teams_info = {}

        def is_test_team(name: str):
            if not name: return False
            lower = name.lower()
            return lower == 'test' or 'equipo de test' in lower or 'equipo test' in lower

        # Mapa para agrupar tareas por equipo y fecha
        # {(team_id, date_str): [valid_programming_tasks]}
        tasks_by_team_date = {}

        def is_excluded_task(description: str):
            if not description: return False
            excluded = ['reunion', 'reunión', 'almuerzo', 'limpieza']
            lower = description.lower()
            return any(term in lower for term in excluded)

        for p in programmings:
            team = p.team
            if not team: continue
            
            team_id = str(team.id)
            team_name = team.name
            
            # Excluir equipos de test
            if is_test_team(team_name): continue
            
            teams_info[team_id] = team_name
            date_str = p.date.strftime("%Y-%m-%d")
            
            key = (team_id, date_str)
            if key not in tasks_by_team_date:
                tasks_by_team_date[key] = []
            
            # Recolectar tareas válidas
            for pt in p.programming_tasks:
                task = pt.task
                if not task or not task.code: continue
                
                desc = task.description or task.code.description or ""
                if is_excluded_task(desc): continue
                
                tasks_by_team_date[key].append(pt)

        # Ahora calcular el rendimiento por cada grupo (equipo+fecha)
        for (team_id, date_str), valid_tasks in tasks_by_team_date.items():
            if not valid_tasks: continue
            
            sum_perf = 0.0
            for pt in valid_tasks:
                task = pt.task
                # Tiempos planeados: Task.minutes o Code.time como fallback
                p_min = float(task.minutes or (task.code.time if task.code else 0.0) or 0.0)
                
                # Tiempos reales con fallbacks
                r_min = float(real_minutes_map.get(str(pt.task_id).lower(), (pt.duration_in_hours or 0.0) * 60))
                if r_min == 0 and pt.real_start_time and pt.real_end_time:
                    delta = pt.real_end_time - pt.real_start_time
                    r_min = delta.total_seconds() / 60.0
                
                # Cantidades (Mismo comportamiento que ReportExcel.tsx)
                # cPlan = (t.quantity && t.quantity > 0) ? t.quantity : 1
                c_plan = float(task.quantity) if (task.quantity and task.quantity > 0) else 1.0
                # cReal = t.real_quantity || 0
                c_real = float(pt.real_quantity or 0.0)
                
                # R = (T.Plan * C.Real) / (T.Real * C.Plan)
                if r_min > 0 and c_plan > 0:
                    sum_perf += (p_min * c_real) / (r_min * c_plan)
            
            # Promedio sobre el total de tareas válidas
            avg_perf = (sum_perf / len(valid_tasks)) * 100.0
            
            if team_id not in perf_matrix:
                perf_matrix[team_id] = {}
            perf_matrix[team_id][date_str] = avg_perf
            active_days.add(date_str)
                
        return {
            "perf_matrix": perf_matrix,
            "active_days": sorted(list(active_days)),
            "teams": [{"id": tid, "name": tname} for tid, tname in teams_info.items()]
        }
    @staticmethod
    def get_last_task(db: Session, programming_id: str):
        """
        Retrieves the last interacted task in a programming.
        Handles 'null' string from frontend gracefully.
        """
        if not programming_id or programming_id == "null":
            return None
            
        try:
            pid = UUID(programming_id) if isinstance(programming_id, str) else programming_id
        except (ValueError, AttributeError):
            return None
            
        # Encontrar la última tarea que tuvo actividad (basado en real_start_time)
        last_pt = db.query(ProgrammingTask).options(
            joinedload(ProgrammingTask.task).joinedload(Task.code)
        ).filter(
            ProgrammingTask.programming_id == pid,
            ProgrammingTask.real_start_time != None
        ).order_by(ProgrammingTask.real_start_time.desc()).first()
        
        # Si no hay ninguna empezada, retornar la primera en orden? 
        # Por ahora solo retornamos la última actividad real.
        if not last_pt:
            return None

        # Serializar mínimamente para el frontend
        task_obj = last_pt.task
        return {
            "id": str(last_pt.task_id),
            "programming_id": str(last_pt.programming_id),
            "real_start_time": last_pt.real_start_time.isoformat() if last_pt.real_start_time else None,
            "real_end_time": last_pt.real_end_time.isoformat() if last_pt.real_end_time else None,
            "is_completed": last_pt.is_completed,
            "task_info": {
                "id": str(task_obj.id),
                "lote": task_obj.lote,
                "description": task_obj.description,
                "code": task_obj.code.code if task_obj.code else None
            } if task_obj else None
        }

programming_service = ProgrammingService()
