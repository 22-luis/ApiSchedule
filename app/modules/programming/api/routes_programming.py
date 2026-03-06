from fastapi import APIRouter, Depends, HTTPException, status, Query, Body, Request
from sqlalchemy import func, and_
from sqlalchemy.orm import Session, joinedload
from typing import List, Optional
from app.modules.programming.models.programming import Programming, ProgrammingTask
from app.modules.programming.models.state import ProgrammingStatus
from app.modules.core.models.role import UserRole
from app.modules.programming.models.task import Task
from app.modules.core.models.team import Team, UserTeam
from app.modules.programming.schemas.programming import ProgrammingCreate, ProgrammingRead, ProgrammingUpdate, ProgrammingTaskOrderIn, ProgrammingReorderResponse, ProgrammingTaskOrderOut, AvailableProgrammingResponse, AvailableProgrammingItem, TasksOrderRequest, ProgrammingTaskReportIn, ToggleTaskStatusRequest, ProgrammingSummaryResponse, ProgrammingSummaryItem
from app.shared.db.session import get_db
from app.shared.utils.core.dependencies import get_current_user, require_roles
from datetime import date, datetime, timedelta, time
from uuid import UUID
from app.modules.programming.schemas.task import TaskOut
from app.modules.core.models.user import User
from app.modules.core.schemas.user import UserOut
import sys
import traceback
from pytz import timezone
from app.shared.utils.business.order_status_service import OrderStatusService
from app.shared.utils.business.programming_availability import update_programming_availability, update_all_programmings_availability_for_date, cleanup_past_programmings, restore_programmings_availability
from app.modules.programming.models.order import Order as OrderModel
from app.modules.programming.models.state import OrderStatus
from app.modules.timer.services.timer import TimerService
from app.modules.timer.models.record_stopwatch import RecordStopwatch
from app.modules.quality.models.test_record import TestRecord as Test

router = APIRouter(prefix="/programmings", tags=["programmings"])

# Helper para verificar si el usuario pertenece al equipo

def user_belongs_to_team(user, team_id):
    return any(str(team.id) == str(team_id) for team in getattr(user, "teams", []))

# Listar programaciones (admin/planner: todas, user: solo su equipo)
@router.get("/", response_model=List[ProgrammingRead])
def list_programmings(db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    privileged_roles = (UserRole.ADMIN, UserRole.PLANNER, UserRole.SUPERVISOR, UserRole.TIMEKEEPER, UserRole.QC_COORDINATOR, UserRole.QC_ASSISTANT)
    if current_user.role in privileged_roles:
        programmings = db.query(Programming).all()
    else:
        team_ids = [team.id for team in getattr(current_user, "teams", [])]
        programmings = db.query(Programming).filter(Programming.team_id.in_(team_ids)).all()
    # Serializar correctamente el campo 'tasks' como lista de UUIDs
    result = []
    for programming in programmings:
        result.append({
            "id": programming.id,
            "date": programming.date,
            "team_id": programming.team_id,
            "tasks": [t.id for t in programming.tasks]
        })
    return result

# Obtener programación por equipo y fecha (debe ir antes del endpoint por id)
@router.get("/by_team_date", response_model=dict)
def get_programming_by_team_date(team_id: str, date: str, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    try:
        # Convertir date a objeto date
        date_obj = datetime.strptime(date, "%Y-%m-%d").date()
        
        # Optimización: Usar joinedload para cargar todas las relaciones en una sola consulta
        programming = db.query(Programming).options(
            joinedload(Programming.programming_tasks).joinedload(ProgrammingTask.task).joinedload(Task.code),
            joinedload(Programming.programming_tasks).joinedload(ProgrammingTask.task).joinedload(Task.created_by_user)
        ).filter_by(team_id=team_id, date=date_obj).first()

        if programming:
            print(f"DEBUG: Found programming {programming.id} for team {team_id} on date {date_obj}")
            print(f"DEBUG: Number of programming_tasks: {len(programming.programming_tasks)}")
        else:
            print(f"DEBUG: No programming found for team {team_id} on date {date_obj}")
        if not programming:
            # Si no existe la programación, verificar si el usuario puede crearla
            privileged_roles = (UserRole.ADMIN, UserRole.PLANNER, UserRole.SUPERVISOR, UserRole.TIMEKEEPER, UserRole.QC_COORDINATOR, UserRole.QC_ASSISTANT)
            if current_user.role not in privileged_roles and not user_belongs_to_team(current_user, team_id):
                raise HTTPException(status_code=403, detail="Not authorized")
            # Crear la programación automáticamente para usuarios autorizados
            programming = Programming(date=date_obj, team_id=team_id)
            db.add(programming)
            db.commit()
            db.refresh(programming)
        else:
            # Si existe la programación, verificar permisos de acceso
            privileged_roles = (UserRole.ADMIN, UserRole.PLANNER, UserRole.SUPERVISOR, UserRole.TIMEKEEPER, UserRole.QC_COORDINATOR, UserRole.QC_ASSISTANT)
            if current_user.role not in privileged_roles and not user_belongs_to_team(current_user, team_id):
                raise HTTPException(status_code=403, detail="Not authorized")

        # Obtener minutos reales acumulados de RecordStopwatch para todas las tareas de esta programación
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

        # Construir la respuesta con los datos ya cargados (sin consultas adicionales)
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
            
            # Properly serialize the created_by_user object
            if task_obj.created_by_user:
                t['created_by_user'] = UserOut.model_validate(task_obj.created_by_user, from_attributes=True).model_dump()
            else:
                t['created_by_user'] = None
            t['is_completed'] = getattr(pt, 'is_completed', None)
            tasks.append(t)
        response = {
            "id": programming.id,
            "date": programming.date,
            "team_id": str(programming.team_id) if not isinstance(programming.team_id, UUID) else programming.team_id,
            "tasks": tasks
        }
        return response
    except Exception as e:
        print("[DEBUG] Exception in get_programming_by_team_date:", e)
        raise

# Endpoint simplificado para obtener solo lote, codigo y descripcion
@router.get("/summary", response_model=ProgrammingSummaryResponse)
def get_programming_summary(team_id: str, date: str, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    try:
        # Convertir date a objeto date
        date_obj = datetime.strptime(date, "%Y-%m-%d").date()
        
        # Optimización: Cargar solo lo necesario
        programming = db.query(Programming).options(
            joinedload(Programming.programming_tasks).joinedload(ProgrammingTask.task).joinedload(Task.code)
        ).filter_by(team_id=team_id, date=date_obj).first()

        if not programming:
            # Si no existe, lanzamos 404 (o podríamos crearla, pero para un "summary" mejor 404)
            raise HTTPException(status_code=404, detail="Programming not found")

        # Verificar permisos
        privileged_roles = (UserRole.ADMIN, UserRole.PLANNER, UserRole.SUPERVISOR, UserRole.TIMEKEEPER, UserRole.QC_COORDINATOR, UserRole.QC_ASSISTANT)
        if current_user.role not in privileged_roles and not user_belongs_to_team(current_user, team_id):
            raise HTTPException(status_code=403, detail="Not authorized")

        # Obtener estados de calidad
        lotes = [str(pt.task.lote) for pt in programming.programming_tasks if pt.task and pt.task.lote]
        quality_map = {}
        if lotes:
            try:
                lote_ints = []
                for l in set(lotes):
                    try:
                        lote_ints.append(int(l))
                    except ValueError:
                        continue
                if lote_ints:
                    tests = db.query(Test).filter(Test.lote.in_(lote_ints)).all()
                    quality_map = {(test.lote, test.code_id): test.status.value if hasattr(test.status, 'value') else str(test.status) for test in tests}
            except Exception as qe:
                print(f"DEBUG: Error fetching quality status for summary: {qe}")

        tasks = []
        for pt in sorted(programming.programming_tasks, key=lambda pt: pt.order):
            task_obj = pt.task
            if not task_obj:
                continue
            
            # Obtener el código desde la relación o el campo fabricationCode
            code_str = task_obj.code.code if task_obj.code else task_obj.fabricationCode
            
            # Si no hay código ni fabricationCode, omitimos la tarea
            if not code_str:
                continue
            
            # Determine quality status
            q_status = None
            try:
                # Convert lote string to int for matching with TestRecord.lote
                lote_int = int(task_obj.lote) if task_obj.lote else None
                
                if lote_int is not None:
                    if task_obj.code_id:
                        # Try specific match (Lote, CodeID)
                        q_status = quality_map.get((lote_int, task_obj.code_id))
                        # Fallback to (Lote, None) if not found
                        if q_status is None:
                            q_status = quality_map.get((lote_int, None))
                    else:
                        # Fallback match
                        q_status = quality_map.get((lote_int, None))
            except (ValueError, TypeError):
                # If lote is not numeric, it won't have a TestRecord anyway
                pass

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
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
    except Exception as e:
        print("[DEBUG] Exception in get_programming_summary:", e)
        raise

# Endpoint optimizado para el dashboard - devuelve todos los datos en una sola consulta
@router.get("/dashboard", response_model=dict)
def get_dashboard_data(date: str, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    """
    Endpoint optimizado que devuelve todos los datos del dashboard en una sola consulta.
    Elimina el problema N+1 del frontend al cargar todas las programaciones con sus tareas
    y relaciones en una sola operación de base de datos.
    """
    try:
        # Convertir date a objeto date
        date_obj = datetime.strptime(date, "%Y-%m-%d").date()
        
        # Determinar qué programaciones puede ver el usuario
        privileged_roles = (UserRole.ADMIN, UserRole.PLANNER, UserRole.SUPERVISOR, UserRole.TIMEKEEPER, UserRole.QC_COORDINATOR, UserRole.QC_ASSISTANT)
        if current_user.role in privileged_roles:
            # Usuarios privilegiados ven todas las programaciones
            programmings_query = db.query(Programming)
        else:
            # Usuarios regulares solo ven las de sus equipos
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
        print("[DEBUG] Exception in get_dashboard_data:", e)
        traceback.print_exc()
        raise

# Obtener una programación
@router.get("/{programming_id}", response_model=ProgrammingRead)
def get_programming(programming_id: UUID, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    programming = db.query(Programming).get(programming_id)
    if not programming:
        raise HTTPException(status_code=404, detail="Programming not found")
    privileged_roles = (UserRole.ADMIN, UserRole.PLANNER, UserRole.SUPERVISOR, UserRole.TIMEKEEPER, UserRole.QC_COORDINATOR, UserRole.QC_ASSISTANT)
    if current_user.role not in privileged_roles and not user_belongs_to_team(current_user, programming.team_id):
        raise HTTPException(status_code=403, detail="Not authorized")
    return {
        "id": programming.id,
        "date": programming.date,
        "team_id": programming.team_id,
        "tasks": [t.id for t in programming.tasks]
    }

# Crear programación (admin/planner/supervisor)
@router.post("/", response_model=ProgrammingRead, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_roles(["admin", "planner", "supervisor"]))])
def create_programming(data: ProgrammingCreate, db: Session = Depends(get_db)):
    # Verificar restricción única
    exists = db.query(Programming).filter_by(date=data.date, team_id=data.team_id).first()
    if exists:
        raise HTTPException(status_code=400, detail="Programming for this team and date already exists")
    programming = Programming(date=data.date, team_id=data.team_id)
    programming.tasks = db.query(Task).filter(Task.id.in_(data.task_ids)).all()
    db.add(programming)
    db.commit()
    db.refresh(programming)
    return programming

# Editar tareas de una programación (admin/planner/supervisor)
@router.put("/{programming_id}", response_model=ProgrammingRead, dependencies=[Depends(require_roles(["admin", "planner", "supervisor"]))])
def update_programming(programming_id: UUID, data: ProgrammingUpdate, db: Session = Depends(get_db)):
    programming = db.query(Programming).get(programming_id)
    if not programming:
        raise HTTPException(status_code=404, detail="Programming not found")
    if data.task_ids is not None:
        programming.tasks = db.query(Task).filter(Task.id.in_(data.task_ids)).all()
    db.commit()
    db.refresh(programming)
    return {
        "id": programming.id,
        "date": programming.date,
        "team_id": programming.team_id,
        "tasks": [t.id for t in programming.tasks]
    }

# Eliminar programación (admin/planner/supervisor)
@router.delete("/{programming_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(require_roles(["admin", "planner", "supervisor"]))])
def delete_programming(programming_id: UUID, db: Session = Depends(get_db)):
    programming = db.query(Programming).get(programming_id)
    if not programming:
        raise HTTPException(status_code=404, detail="Programming not found")
    db.delete(programming)
    db.commit()
    return None

@router.post("/ensure_by_team_date", response_model=ProgrammingRead)
def ensure_programming_by_team_date(team_id: str = Query(...), date: date = Query(...), db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    programming = db.query(Programming).filter_by(team_id=team_id, date=date).first()
    if programming:
        return {
            "id": programming.id,
            "date": programming.date,
            "team_id": programming.team_id,
            "tasks": [t.id for t in programming.tasks]
        }
    # Solo admin/planner/supervisor pueden crear
    if current_user.role not in (UserRole.ADMIN, UserRole.PLANNER, UserRole.SUPERVISOR):
        raise HTTPException(status_code=403, detail="Not authorized to create programming")
    programming = Programming(date=date, team_id=team_id)
    db.add(programming)
    db.commit()
    db.refresh(programming)
    return {
        "id": programming.id,
        "date": programming.date,
        "team_id": programming.team_id,
        "tasks": [t.id for t in programming.tasks]
    } 

@router.post("/{programming_id}/add_task", response_model=ProgrammingRead)
def add_task_to_programming(
    programming_id: UUID,
    task_id: str = Body(..., embed=True),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    programming = db.query(Programming).get(programming_id)
    if not programming:
        raise HTTPException(status_code=404, detail="Programming not found")
    if current_user.role not in (UserRole.ADMIN, UserRole.PLANNER, UserRole.SUPERVISOR):
        raise HTTPException(status_code=403, detail="Not authorized")
    task = db.query(Task).get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    if task not in programming.tasks:
        programming.tasks.append(task)
        db.commit()
        
        # Update programming availability after adding task
        update_programming_availability(db, programming)
        
        db.refresh(programming)
    return {
        "id": programming.id,
        "date": programming.date,
        "team_id": programming.team_id,
        "tasks": [t.id for t in programming.tasks]
    } 

@router.post("/{programming_id}/remove_task", response_model=ProgrammingRead)
def remove_task_from_programming(
    programming_id: UUID,
    task_id: str = Body(..., embed=True),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    programming = db.query(Programming).get(programming_id)
    if not programming:
        raise HTTPException(status_code=404, detail="Programming not found")
    if current_user.role not in (UserRole.ADMIN, UserRole.PLANNER, UserRole.SUPERVISOR):
        raise HTTPException(status_code=403, detail="Not authorized")
    task = db.query(Task).get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    if task in programming.tasks:
        programming.tasks.remove(task)
        db.commit()
        
        # Update programming availability after removing task
        update_programming_availability(db, programming)
        
        db.refresh(programming)
    return {
        "id": programming.id,
        "date": programming.date,
        "team_id": programming.team_id,
        "tasks": [t.id for t in programming.tasks]
    } 

@router.put("/{programming_id}/reorder", response_model=ProgrammingReorderResponse)
async def reorder_programming_tasks(
    programming_id: UUID,
    request: Request,
    data: TasksOrderRequest = Body(...),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(UserRole.ADMIN, UserRole.PLANNER, UserRole.SUPERVISOR))
):
    tasks_order = data.tasks_order
    raw_body = await request.body()
    print("RAW PAYLOAD (antes de parsear):", raw_body)
    print("PARSED tasks_order:", tasks_order, file=sys.stderr)
    programming = db.query(Programming).get(programming_id)
    if not programming:
        raise HTTPException(status_code=404, detail="Programming not found")
    programming_tasks_map = {pt.task_id: pt for pt in programming.programming_tasks}
    result = []
    current_time = None
    base_time = None # Fix for undefined base_time
    sv_tz = timezone("America/El_Salvador")
    for item in sorted(tasks_order, key=lambda x: x.order):
        pt = programming_tasks_map.get(item.task_id)
        if not pt:
            raise HTTPException(status_code=404, detail=f"Task {item.task_id} not found in programming")
        pt.order = item.order
        pt.duration_in_hours = item.duration_in_hours
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
                if base_time:
                    base_hour, base_minute = map(int, base_time.split(":"))
                    current_time = datetime.combine(programming_date, time(base_hour, base_minute))
                else:
                    if weekday == 5:
                        current_time = datetime.combine(programming_date, time(7, 30))
                    else:
                        current_time = datetime.combine(programming_date, time(7, 0))
            
            # Ajustar inicio si cae en el almuerzo
            curr_mins = current_time.hour * 60 + current_time.minute
            if 720 <= curr_mins < 780:
                current_time = datetime.combine(programming_date, time(13, 0))
            
            pt.start_time = current_time
            duration = getattr(pt.task, "minutes", 0) or 0
            
            # Usar la utilidad central para calcular el fin con el ajuste de almuerzo
            from app.modules.automation.services.utils.programming_utils import ProgrammingUtils
            pt.end_time = ProgrammingUtils.adjust_for_lunch_break(current_time, duration)
            current_time = pt.end_time
        result.append(ProgrammingTaskOrderOut(
            task_id=pt.task_id,
            order=pt.order,
            start_time=pt.start_time,
            end_time=pt.end_time,
            duration_in_hours=pt.duration_in_hours
        ))
    db.commit()
    
    # Update programming availability after reordering tasks
    update_programming_availability(db, programming)
    
    return ProgrammingReorderResponse(
        programming_id=programming_id,
        tasks=result
    )

@router.get("/{programming_id}/last_task", response_model=dict)
def get_last_task_of_programming(programming_id: UUID, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    programming = db.query(Programming).get(programming_id)
    if not programming:
        raise HTTPException(status_code=404, detail="Programming not found")
    # Buscar la ProgrammingTask con mayor end_time para esa programación
    last_prog_task = (
        db.query(ProgrammingTask)
        .filter(ProgrammingTask.programming_id == programming_id)
        .order_by(ProgrammingTask.end_time.desc().nullslast())
        .first()
    )
    if not last_prog_task:
        raise HTTPException(status_code=404, detail="No tasks found for this programming")
    last_task = db.query(Task).filter(Task.id == last_prog_task.task_id).first()
    task_out = TaskOut.model_validate(last_task, from_attributes=True).model_dump()
    task_out['programming_end_time'] = last_prog_task.end_time.isoformat() if last_prog_task.end_time is not None else None
    return task_out 

@router.post("/{programming_id}/tasks/{task_id}/start_timer")
def start_task_timer(programming_id: str, task_id: str, data: dict = Body(None), db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    pt = db.query(ProgrammingTask).filter_by(programming_id=programming_id, task_id=task_id).first()
    if not pt:
        raise HTTPException(status_code=404, detail="ProgrammingTask not found")
    sv_tz = timezone("America/El_Salvador")
    if data and data.get("real_start_time"):
        val = data["real_start_time"]
        if isinstance(val, str):
            pt.real_start_time = datetime.fromisoformat(val)
        else:
            pt.real_start_time = val
    else:
        pt.real_start_time = datetime.now(sv_tz)
    pt.completed_by_user_id = current_user.id
    
    # Actualizar estado de la orden usando el servicio centralizado
    OrderStatusService.update_order_status_for_task_start(db, pt)
    
    db.commit()
    return {"ok": True, "real_start_time": pt.real_start_time}

@router.post("/{programming_id}/tasks/{task_id}/stop_timer")
def stop_task_timer(programming_id: str, task_id: str, data: ProgrammingTaskReportIn = Body(...), db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    # Cargar ProgrammingTask con la tarea relacionada
    pt = db.query(ProgrammingTask).options(
        joinedload(ProgrammingTask.task)
    ).filter_by(
        programming_id=programming_id,
        task_id=task_id
    ).first()

    if not pt:
        raise HTTPException(status_code=404, detail="ProgrammingTask not found")
    
    sv_tz = timezone("America/El_Salvador")
    if hasattr(data, 'real_end_time') and data.real_end_time:
        val = data.real_end_time
        if isinstance(val, str):
            pt.real_end_time = datetime.fromisoformat(val)
        else:
            pt.real_end_time = val
    else:
        pt.real_end_time = datetime.now(sv_tz)
    # Si real_quantity es una cadena vacía o None, establecer como None
    pt.real_quantity = None if data.real_quantity is None or (isinstance(data.real_quantity, str) and data.real_quantity.strip() == "") else data.real_quantity

    lote = None
    has_pending_tasks = None
    # Si se establece real_end_time, evaluar autocompletado para tareas sin cantidad
    if pt.real_end_time:
        # Use the current user as the completer when we auto-complete
        completer_id = current_user.id

        # Nueva lógica más clara para determinar si una tarea tiene cantidad asignada
        task_has_quantity = False
        quantity_value = None
        
        # Verificación detallada de la cantidad
        task_has_quantity = False
        quantity_value = None
        
        if pt.task:
            # Verificar si la cantidad es None o cadena vacía
            if pt.task.quantity is None or (isinstance(pt.task.quantity, str) and pt.task.quantity.strip() == ""):
                print(f"DEBUG - Quantity is None or empty string")
                task_has_quantity = False
            else:
                try:
                    # Intentar convertir a float
                    raw_quantity = pt.task.quantity if not isinstance(pt.task.quantity, str) else pt.task.quantity.strip()
                    quantity_value = float(raw_quantity)
                    task_has_quantity = quantity_value > 0
                    print(f"DEBUG - Parsed quantity value: {quantity_value}")
                    print(f"DEBUG - Task has quantity: {task_has_quantity}")
                except (ValueError, TypeError) as e:
                    print(f"DEBUG - Error parsing quantity: {e}")
                    task_has_quantity = False

        try:
            print(f"DEBUG - Evaluating completion conditions:")
            
            # Verificar condiciones para autocompletar
            should_complete = False
            completion_reason = ""
            
            if not task_has_quantity:
                # Caso 1: Tarea sin cantidad configurada
                should_complete = True
                completion_reason = "Task has no quantity configured"
            elif pt.real_quantity is not None:
                # Caso 2: Tarea tiene cantidad real reportada
                # Solo completar si la cantidad real alcanza la asignada (si existe)
                try:
                    assigned_qty = None
                    if pt.task and pt.task.quantity is not None:
                        assigned_qty = float(pt.task.quantity)
                    real_qty = float(pt.real_quantity)
                    print(f"DEBUG - Quantity check - assigned: {assigned_qty}, real: {real_qty}")
                    if assigned_qty is None or assigned_qty == 0:
                        # Sin cantidad asignada significativa -> completar
                        should_complete = True
                        completion_reason = "Task has real quantity and no meaningful assigned qty"
                    else:
                        # Completar solo si real >= assigned
                        if real_qty >= assigned_qty:
                            should_complete = True
                            completion_reason = "Real qty >= assigned qty"
                        else:
                            should_complete = False
                            completion_reason = f"Real qty ({real_qty}) < assigned ({assigned_qty})"
                except (ValueError, TypeError) as e:
                    print(f"DEBUG - Error parsing quantities: {e}")
                    should_complete = False
                    completion_reason = "Error parsing quantities"
            else:
                # Caso 3: Tarea necesita cantidad pero no tiene cantidad real
                should_complete = False
                completion_reason = "Task needs quantity but no real quantity reported"
                
            # Aplicar la decisión
            if should_complete:
                # Marcar como completada
                pt.is_completed = True
                pt.completed_by_user_id = completer_id
                print(f"DEBUG - Task marked as completed:")
                print(f"DEBUG - is_completed set to: {pt.is_completed}")
                print(f"DEBUG - completed_by_user_id set to: {completer_id}")
                
                # Actualizar tarea principal si existe
                if pt.task:
                    pt.task.is_completed = True
                    lote = pt.task.lote
                    print(f"DEBUG - Master task updated:")
                    print(f"DEBUG - Master task is_completed: {pt.task.is_completed}")
                    print(f"DEBUG - Lote: {lote}")
            else:
                # Marcar como incompleta
                pt.is_completed = False
                pt.completed_by_user_id = None
                
                # Verificar tareas pendientes de manera más robusta
                try:
                    incomplete_tasks = db.query(ProgrammingTask).filter(
                        ProgrammingTask.programming_id == pt.programming_id,
                        ProgrammingTask.is_completed == False
                    ).count()
                    has_pending_tasks = incomplete_tasks > 0
                except Exception as e:
                    has_pending_tasks = True  # Por seguridad, asumimos que hay tareas pendientes

            # Hacer commit de los cambios inmediatamente
            try:
                db.commit()
                print(f"DEBUG - Changes committed successfully")
            except Exception as e:
                print(f"DEBUG - Error in commit: {e}")
                db.rollback()
                raise

        except Exception as e:
            print(f"DEBUG - Error in auto-completion logic: {e}")
            traceback.print_exc()
            db.rollback()
            # If we have persisted a state, return it to the client instead of 500
            try:
                db.refresh(pt)
                return {"ok": True, "real_end_time": getattr(pt, 'real_end_time', None), "real_quantity": getattr(pt, 'real_quantity', None), "lote": getattr(pt.task, 'lote', None) if pt.task else None, "has_pending_tasks": has_pending_tasks, "is_completed": bool(getattr(pt, 'is_completed', False)), "warning": "Error during auto-completion processing"}
            except Exception:
                raise HTTPException(status_code=500, detail="Error processing task completion")

    # Primer commit para guardar los cambios de la tarea actual
    db.commit()
    
    # Ahora que la tarea actual está guardada, verificamos las tareas pendientes
    # Actualizar estado de la orden usando el servicio centralizado
    # Eliminamos la lógica manual anterior para evitar conflictos y centralizar en el servicio
    
    # Actualizar estado de la orden usando el servicio centralizado
    try:
        OrderStatusService.update_order_status_for_task_completion(db, pt)
    except Exception as e:
        # Registrar el error pero no bloquear la respuesta del endpoint
        print(f"DEBUG - Error updating order status in stop_timer: {e}")

    # Commit final para asegurar que todos los cambios se guarden
    try:
        db.commit()
    except Exception as e:
        print(f"DEBUG - Error in final commit after stop_timer: {e}")
        db.rollback()
        raise
    # Refrescar el objeto para asegurar que devolvemos el estado actualizado
    try:
        db.refresh(pt)
    except Exception:
        # Si refresh falla, no bloqueamos la respuesta, pero lo registramos
        print(f"DEBUG - Warning: could not refresh ProgrammingTask {pt.programming_id}/{pt.task_id}")

    return {"ok": True, "real_end_time": pt.real_end_time, "real_quantity": pt.real_quantity, "lote": lote, "has_pending_tasks": has_pending_tasks, "is_completed": bool(pt.is_completed)}

@router.post("/{programming_id}/tasks/{task_id}/comment")
def add_task_comment(programming_id: str, task_id: str, data: ProgrammingTaskReportIn = Body(...), db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    pt = db.query(ProgrammingTask).filter_by(programming_id=programming_id, task_id=task_id).first()
    if not pt:
        raise HTTPException(status_code=404, detail="ProgrammingTask not found")
    programming = db.query(Programming).get(programming_id)
    if not programming:
        raise HTTPException(status_code=404, detail="Programming not found")

    privileged_roles = (UserRole.ADMIN, UserRole.PLANNER, UserRole.SUPERVISOR, UserRole.TIMEKEEPER)
    if current_user.role not in privileged_roles and not user_belongs_to_team(current_user, programming.team_id):
        raise HTTPException(status_code=403, detail="Not authorized to comment on this task")
    
    pt.comment = data.comment
    db.commit()
    return {"ok": True, "comment": pt.comment}

@router.post("/{programming_id}/tasks/{task_id}/toggle_status")
def toggle_task_status(programming_id: str, task_id: str, data: Optional[ToggleTaskStatusRequest] = Body(None), db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    try:
        # Cargar ProgrammingTask con todas las relaciones necesarias
        pt = (
            db.query(ProgrammingTask)
            .options(
                joinedload(ProgrammingTask.task),
                joinedload(ProgrammingTask.programming)
            )
            .filter_by(programming_id=programming_id, task_id=task_id)
            .first()
        )
        
        if not pt:
            raise HTTPException(status_code=404, detail="ProgrammingTask not found")
        
        print(f"DEBUG - Initial Task State:")
        print(f"DEBUG - Task ID: {pt.task_id}")
        print(f"DEBUG - Current is_completed: {pt.is_completed}")
        print(f"DEBUG - Current type: {type(pt.is_completed)}")
        print(f"DEBUG - Task quantity: {pt.task.quantity if pt.task else None}")
        print(f"DEBUG - Real quantity: {pt.real_quantity}")
        print(f"DEBUG - Real start time: {pt.real_start_time}")
        print(f"DEBUG - Real end time: {pt.real_end_time}")
        
        # Roles que pueden modificar cualquier tarea
        privileged_roles = (UserRole.ADMIN, UserRole.PLANNER, UserRole.SUPERVISOR)
        
        # Verificar que el usuario tenga permisos para modificar esta tarea
        if current_user.role not in privileged_roles:
            if pt.completed_by_user_id and pt.completed_by_user_id != current_user.id:
                print(f"DEBUG - Authorization check failed:")
                print(f"DEBUG - User role: {current_user.role.value}")
                print(f"DEBUG - Task completed_by_user_id: {pt.completed_by_user_id}")
                print(f"DEBUG - Current user ID: {current_user.id}")
                raise HTTPException(status_code=403, detail="No autorizado")
        # Actualizar cantidades si se proporcionan en el body
        if data:
            if data.assigned_quantity is not None and pt.task:
                print(f"DEBUG - Updating assigned_quantity to {data.assigned_quantity}")
                pt.task.quantity = data.assigned_quantity
                # Opcionalmente, recalcular duration/assigned_quantity localmente si fuera necesario, 
                # pero por ahora solo actualizamos el valor.
            
            if data.real_quantity is not None:
                print(f"DEBUG - Updating real_quantity to {data.real_quantity}")
                pt.real_quantity = data.real_quantity

        # Realizar el toggle del estado
        try:
            print(f"DEBUG - Analyzing task completion conditions:")
            
            # 1. Verificar si la tarea tiene cantidad configurada
            has_quantity = False
            if pt.task and pt.task.quantity is not None:
                try:
                    quantity = float(pt.task.quantity) if isinstance(pt.task.quantity, str) else pt.task.quantity
                    has_quantity = quantity > 0
                except (ValueError, TypeError):
                    has_quantity = False
            
            print(f"DEBUG - Task has quantity configured: {has_quantity}")
            
            # 2. Verificar si la tarea está completada actualmente
            current_is_completed = bool(pt.is_completed)
            print(f"DEBUG - Current completion status: {current_is_completed}")
            
            # 3. Determinar si se puede cambiar el estado
            can_toggle = True
            toggle_message = ""
            
            # Si la tarea está completada, siempre se puede descompletar
            if current_is_completed:
                can_toggle = True
                toggle_message = "Task can be uncompleted"
            else:
                # Si la tarea no está completada, verificar condiciones
                if not has_quantity:
                    # Tarea sin cantidad - puede completarse si tiene tiempo real
                    can_toggle = pt.real_start_time is not None and pt.real_end_time is not None
                    toggle_message = "Task without quantity - needs real times"
                else:
                    # Tarea con cantidad - necesita cantidad real y además real >= asignada
                    try:
                        assigned = None
                        if pt.task and pt.task.quantity is not None:
                            assigned = float(pt.task.quantity)
                        real = float(pt.real_quantity) if pt.real_quantity is not None else None
                        if assigned is None or assigned == 0:
                            # Si no hay cantidad asignada significativa, requerir tiempos reales
                            can_toggle = pt.real_start_time is not None and pt.real_end_time is not None
                            toggle_message = "Task has no meaningful assigned quantity - needs real times"
                        else:
                            # For privileged users, allow toggling even if quantity is not met
                            if current_user.role.value in privileged_roles:
                                can_toggle = True
                                toggle_message = "Privileged user override"
                            else:
                                can_toggle = (real is not None and real >= assigned)
                                toggle_message = f"Task with quantity - needs real quantity >= assigned ({assigned})"
                    except (ValueError, TypeError) as e:
                        can_toggle = False
                        toggle_message = f"Error parsing quantities: {e}"
            
            print(f"DEBUG - Toggle decision:")
            print(f"DEBUG - Can toggle: {can_toggle}")
            print(f"DEBUG - Reason: {toggle_message}")
                
            # 4. Realizar el toggle si es posible
            if can_toggle:
                new_is_completed = not current_is_completed
                
                print(f"DEBUG - Performing state toggle:")
                print(f"DEBUG - Current state: {current_is_completed}")
                print(f"DEBUG - New state: {new_is_completed}")
                
                # Establecer el nuevo estado
                pt.is_completed = new_is_completed
                
                # Actualizar completed_by_user_id
                if new_is_completed:
                    pt.completed_by_user_id = current_user.id
                    print(f"DEBUG - Set completed_by_user_id: {current_user.id}")
                else:
                    pt.completed_by_user_id = None
                    print(f"DEBUG - Cleared completed_by_user_id")
                
                # Actualizar tarea principal si existe
                if pt.task:
                    pt.task.is_completed = new_is_completed
                    print(f"DEBUG - Updated master task status: {new_is_completed}")
            else:
                print(f"DEBUG - Cannot toggle state: {toggle_message}")
                raise HTTPException(status_code=400, detail=toggle_message)            # Actualizar la tarea principal si existe
            if pt.task:
                pt.task.is_completed = new_is_completed
                print(f"DEBUG - Updated master task. New state: {pt.task.is_completed}")
            
            # Gestionar el completed_by_user_id
            if new_is_completed:
                pt.completed_by_user_id = current_user.id
                print(f"DEBUG - Set completed_by_user_id to: {current_user.id}")
            else:
                pt.completed_by_user_id = None
                print(f"DEBUG - Cleared completed_by_user_id")
            
            # Primer commit para guardar los cambios básicos
            db.commit()
            print(f"DEBUG - Basic changes committed")
            
            # Refrescar para verificar
            db.refresh(pt)
            print(f"DEBUG - State after refresh: {pt.is_completed}")
            
            # Actualizar estado de la orden solo si hay un lote válido
            try:
                # Obtener el lote de la tarea principal
                lote = pt.task.lote if pt.task else None
                print(f"DEBUG - Task lote value: {lote}")
                
                # Solo actualizar el estado si el lote es válido
                if lote and lote != "-" and lote.strip():
                    try:
                        OrderStatusService.update_order_status_for_task_completion(db, pt)
                        db.commit()
                        print(f"DEBUG - Order status updated for lote: {lote}")
                    except Exception as e:
                        print(f"DEBUG - Error updating order status: {str(e)}")
                        # No hacemos rollback aquí
                else:
                    print(f"DEBUG - Skipping order status update - invalid lote: {lote}")
            except Exception as e:
                print(f"DEBUG - Error checking lote: {str(e)}")
                # No hacemos rollback aquí
            
            # Refrescar una última vez
            db.refresh(pt)
            final_status = bool(pt.is_completed)
            print(f"DEBUG - Final state: {final_status}")
            
            return {"is_completed": final_status}
            
        except Exception as e:
            print(f"DEBUG - Error in toggle operation: {str(e)}")
            traceback.print_exc()
            db.rollback()
            # Return current known state instead of raising 500 so frontend can continue
            try:
                current_state = bool(pt.is_completed)
            except Exception:
                current_state = False
            return {"is_completed": current_state, "error": "Error toggling status"}
            
    except HTTPException as he:
        raise he
    except Exception as e:
        print(f"DEBUG - Unexpected error: {str(e)}")
        traceback.print_exc()
        # If possible, return the current is_completed to avoid 500 when state was persisted
        try:
            current_state = bool(pt.is_completed)
        except Exception:
            current_state = False
        return {"is_completed": current_state, "error": "Unexpected error"}

@router.post("/{programming_id}/tasks/{task_id}/reprogram")
def reprogram_task(
    programming_id: str, 
    task_id: str, 
    new_date: date,
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user)
):
    pt = db.query(ProgrammingTask).filter_by(programming_id=programming_id, task_id=task_id).first()
    if not pt:
        raise HTTPException(status_code=404, detail="ProgrammingTask not found")
    
    # Actualizar estado de la orden antes de reprogramar
    OrderStatusService.update_order_status_for_task_reprogramming(db, pt, new_date)
    
    return {"message": "Task reprogrammed successfully"}



# Manually check and update programming availability based on the last task's end time.
@router.post("/{programming_id}/check_availability")
def check_programming_availability(
    programming_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["admin", "planner", "supervisor"]))
):
    programming = db.query(Programming).get(programming_id)
    if not programming:
        raise HTTPException(status_code=404, detail="Programming not found")
    
    # Update programming availability
    status_changed = update_programming_availability(db, programming)
    
    return {
        "programming_id": programming_id,
        "current_status": programming.status.value,
        "status_changed": status_changed
    }



# Check and update availability for all programmings on a specific date.
@router.post("/check_availability_by_date")
def check_programmings_availability_by_date(
    target_date: date,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["admin", "planner", "supervisor"]))
):
    results = update_all_programmings_availability_for_date(db, target_date)
    
    return {
        "target_date": target_date.isoformat(),
        "results": results
    } 

@router.get("/team/{team_uuid}/available", response_model=AvailableProgrammingResponse)
def get_available_programmings_for_team(
    team_uuid: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    # Verificar que el equipo existe
    team = db.query(Team).filter(Team.id == team_uuid).first()
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    
    # Verificar permisos del usuario
    if current_user.role.value not in ("admin", "planner", "supervisor", "timekeeper") and not user_belongs_to_team(current_user, team_uuid):
        raise HTTPException(status_code=403, detail="Not authorized to access this team")
    
    # Obtener la fecha actual
    current_date = date.today()
    
    # Buscar programaciones disponibles desde la fecha actual
    available_programmings = (
        db.query(Programming)
        .filter(
            Programming.team_id == team_uuid,
            Programming.date >= current_date,
            Programming.status == ProgrammingStatus.available
        )
        .order_by(Programming.date)
        .all()
    )
    
    # Si no hay programaciones futuras disponibles, buscar la última programación del equipo
    if not available_programmings:
        last_programming = (
            db.query(Programming)
            .filter(Programming.team_id == team_uuid)
            .order_by(Programming.date.desc())
            .first()
        )
        
        # Si no hay ninguna programación, crear una para mañana
        if not last_programming:
            next_date = current_date + timedelta(days=1)
        else:
            # Crear una programación para el día siguiente a la última
            next_date = last_programming.date + timedelta(days=1)
        
        # Crear la nueva programación
        new_programming = Programming(
            date=next_date,
            team_id=team_uuid,
            status=ProgrammingStatus.available
        )
        db.add(new_programming)
        db.commit()
        db.refresh(new_programming)
        
        # Agregar la nueva programación a la lista
        available_programmings = [new_programming]
    
    # Preparar la respuesta usando el schema
    available_items = []
    for programming in available_programmings:
        available_items.append(AvailableProgrammingItem(
            id=str(programming.id),
            team_name=team.name,
            date=programming.date.isoformat()
        ))
    
    return AvailableProgrammingResponse(
        team_id=str(team_uuid),
        team_name=team.name,
        available_programmings=available_items
    )

@router.get("/team/{team_uuid}/available-only", response_model=AvailableProgrammingResponse)
def get_only_available_programmings_for_team(
    team_uuid: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    # Verificar que el equipo existe
    team = db.query(Team).filter(Team.id == team_uuid).first()
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    
    # Verificar permisos del usuario
    if current_user.role.value not in ("admin", "planner", "supervisor", "timekeeper") and not user_belongs_to_team(current_user, team_uuid):
        raise HTTPException(status_code=403, detail="Not authorized to access this team")
    
    # Obtener la fecha actual
    current_date = date.today()
    
    # Buscar programaciones disponibles desde la fecha actual
    available_programmings = (
        db.query(Programming)
        .filter(
            Programming.team_id == team_uuid,
            Programming.date >= current_date,
            Programming.status == ProgrammingStatus.available
        )
        .order_by(Programming.date)
        .all()
    )
    
    # Preparar la respuesta usando el schema
    available_items = []
    for programming in available_programmings:
        available_items.append(AvailableProgrammingItem(
            id=str(programming.id),
            team_name=team.name,
            date=programming.date.isoformat()
        ))
    
    return AvailableProgrammingResponse(
        team_id=str(team_uuid),
        team_name=team.name,
        available_programmings=available_items
    )

@router.post("/team/{team_uuid}/create-next-available", response_model=AvailableProgrammingItem)
def create_next_available_programming_for_team(
    team_uuid: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(["admin", "planner", "supervisor"]))
):
    # Verificar que el equipo existe
    team = db.query(Team).filter(Team.id == team_uuid).first()
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    
    # Buscar la última programación del equipo
    last_programming = (
        db.query(Programming)
        .filter(Programming.team_id == team_uuid)
        .order_by(Programming.date.desc())
        .first()
    )
    
    # Determinar la fecha para la nueva programación
    if not last_programming:
        next_date = date.today() + timedelta(days=1)
    else:
        next_date = last_programming.date + timedelta(days=1)
    
    # Verificar que no exista ya una programación para esa fecha
    existing_programming = (
        db.query(Programming)
        .filter(Programming.team_id == team_uuid, Programming.date == next_date)
        .first()
    )
    
    if existing_programming:
        raise HTTPException(
            status_code=400, 
            detail=f"Programming already exists for team {team.name} on date {next_date}"
        )
    
    # Crear la nueva programación
    new_programming = Programming(
        date=next_date,
        team_id=team_uuid,
        status=ProgrammingStatus.available
    )
    db.add(new_programming)
    db.commit()
    db.refresh(new_programming)
    
    return AvailableProgrammingItem(
        id=str(new_programming.id),
        team_name=team.name,
        date=new_programming.date.isoformat()
    )

@router.get("/{programming_id}/next-available-time", response_model=dict)
def get_next_available_time_for_programming(
    programming_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    from datetime import time
    
    # Verificar que la programación existe
    programming = db.query(Programming).get(programming_id)
    if not programming:
        raise HTTPException(status_code=404, detail="Programming not found")
    
    # Verificar permisos del usuario
    if current_user.role.value not in ("admin", "planner", "supervisor", "timekeeper") and not user_belongs_to_team(current_user, str(programming.team_id)):
        raise HTTPException(status_code=403, detail="Not authorized to access this programming")
    
    # Obtener las tareas de la programación ordenadas por end_time
    programming_tasks = (
        db.query(ProgrammingTask)
        .filter(ProgrammingTask.programming_id == programming_id)
        .order_by(ProgrammingTask.end_time.desc().nullslast())
        .all()
    )
    
    # Calcular el siguiente horario disponible
    programming_date: date = programming.date
    if not programming_tasks:
        # Programación vacía - siguiente horario disponible es 7:00
        next_available_time = datetime.combine(programming_date, time(7, 0))
        message = "Programación vacía - siguiente horario disponible: 7:00"
    else:
        # Obtener la última tarea
        last_task = programming_tasks[0]  # Ya está ordenado por end_time desc
        
        if last_task.end_time:
            next_available_time = last_task.end_time
            message = f"Siguiente horario disponible después de la última tarea: {last_task.end_time.strftime('%H:%M')}"
        else:
            # Si la última tarea no tiene end_time, usar 7:00
            next_available_time = datetime.combine(programming_date, time(7, 0))
            message = "Última tarea sin horario - siguiente horario disponible: 7:00"
    
    # Obtener información del equipo
    team = db.query(Team).filter(Team.id == programming.team_id).first()
    team_name = team.name if team else "Equipo desconocido"
    
    return {
        "success": True,
        "message": message,
        "programming_id": str(programming_id),
        "team_id": str(programming.team_id),
        "team_name": team_name,
        "date": programming.date.isoformat(),
        "next_available_time": next_available_time.isoformat(),
        "next_available_time_formatted": next_available_time.strftime("%H:%M"),
        "total_tasks": len(programming_tasks),
        "is_empty": len(programming_tasks) == 0
    }

@router.get("/team/{team_id}/first-available-for-task", response_model=dict)
def get_first_available_programming_for_task(
    team_id: UUID,
    task_minutes: int = Query(..., description="Duración de la tarea en minutos"),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    from datetime import time
    
    # Verificar que el equipo existe
    team = db.query(Team).filter(Team.id == team_id).first()
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    
    # Verificar permisos del usuario
    if current_user.role.value not in ("admin", "planner", "supervisor", "timekeeper") and not user_belongs_to_team(current_user, str(team_id)):
        raise HTTPException(status_code=403, detail="Not authorized to access this team")
    
    # Obtener todas las programaciones disponibles del equipo
    available_programmings = (
        db.query(Programming)
        .filter(
            Programming.team_id == team_id,
            Programming.status == ProgrammingStatus.available
        )
        .order_by(Programming.date)
        .all()
    )
    
    if not available_programmings:
        return {
            "success": False,
            "message": "No hay programaciones disponibles para este equipo",
            "selected_programming": None
        }
    
    # Configurar límites de tiempo
    time_limit = time(17, 40)  # 17:40
    tolerance_minutes = 5
    max_allowed_minutes = time_limit.hour * 60 + time_limit.minute + tolerance_minutes
    
    # Evaluar cada programación en orden para encontrar la primera que cumpla
    for programming in available_programmings:
        # Obtener las tareas de la programación
        programming_tasks = (
            db.query(ProgrammingTask)
            .filter(ProgrammingTask.programming_id == programming.id)
            .all()
        )
        
        # Calcular el tiempo actual de la programación
        current_end_minutes = 0
        
        if not programming_tasks:
            # Programación vacía - tiempo de inicio (7:00) + tarea de preparación (10 min)
            current_end_minutes = 7 * 60 + 10  # 7:10
        else:
            # Ordenar tareas por end_time y obtener la última
            sorted_tasks = sorted(programming_tasks, key=lambda x: x.end_time if x.end_time else time(0, 0))
            last_task = sorted_tasks[-1]
            
            if last_task.end_time:
                current_end_minutes = last_task.end_time.hour * 60 + last_task.end_time.minute
            else:
                current_end_minutes = 7 * 60  # 7:00
        
        # Calcular el tiempo final si se agrega la nueva tarea
        final_minutes = current_end_minutes + task_minutes
        
        # Ajustar por almuerzo (12:00 PM - 1:00 PM)
        # 12:00 PM = 720 minutos, 1:00 PM = 780 minutos desde la medianoche
        if current_end_minutes < 720 and final_minutes > 720:
            final_minutes += 60
        elif 720 <= current_end_minutes < 780:
            # Si el inicio actual cae en el almuerzo, mover a la 1 PM + duración de la tarea
            final_minutes = 780 + task_minutes
        
        # Verificar si esta programación cumple con el límite
        if final_minutes <= max_allowed_minutes:
            # ¡Encontramos la primera programación que cumple!
            current_end_time = time(current_end_minutes // 60, current_end_minutes % 60)
            final_time = time(final_minutes // 60, final_minutes % 60)
            
            return {
                "success": True,
                "message": f"Primera programación disponible encontrada que cumple con límite de tiempo",
                "selected_programming": {
                    "id": str(programming.id),
                    "date": programming.date.isoformat(),
                    "team_id": str(programming.team_id),
                    "team_name": team.name,
                    "current_end_time": current_end_time.isoformat(),
                    "task_minutes": task_minutes,
                    "final_time": final_time.isoformat(),
                    "time_limit": time_limit.isoformat(),
                    "tolerance_minutes": tolerance_minutes,
                    "total_existing_tasks": len(programming_tasks),
                    "is_empty": len(programming_tasks) == 0
                },
                "verification_details": {
                    "current_end_minutes": current_end_minutes,
                    "final_minutes": final_minutes,
                    "max_allowed_minutes": max_allowed_minutes,
                    "within_limit": True
                }
            }
    
    # Si ninguna programación cumple con el límite
    return {
        "success": False,
        "message": "Ninguna programación disponible cumple con el límite de tiempo",
        "selected_programming": None
    }


# Cleanup past programmings (mark all past dates as unavailable)
@router.post("/cleanup_past")
def cleanup_past_programmings_endpoint(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.PLANNER, UserRole.SUPERVISOR))
):
    """
    Marks all programmings with dates in the past as unavailable.
    This endpoint can be called manually or via a scheduled job.
    """
    results = cleanup_past_programmings(db)
    
    return {
        "message": "Past programmings cleanup completed",
        "results": results
    }

@router.post("/restore_availability")
def restore_availability_endpoint(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.PLANNER, UserRole.SUPERVISOR))
):
    """
    Restaura la disponibilidad de las programaciones futuras que tienen espacio.
    """
    results = restore_programmings_availability(db)
    
    return {
        "message": "Availability restoration completed",
        "results": results
    }

@router.patch("/{programming_id}/tasks/{task_id}/quantity")
def update_task_quantity(
    programming_id: UUID,
    task_id: UUID,
    data: dict = Body(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.PLANNER, UserRole.SUPERVISOR))
):
    pt = db.query(ProgrammingTask).filter_by(programming_id=programming_id, task_id=task_id).first()
    if not pt:
        raise HTTPException(status_code=404, detail="ProgrammingTask not found")
    
    real_quantity = data.get("real_quantity")
    if real_quantity is not None:
        try:
            pt.real_quantity = float(real_quantity)
        except (ValueError, TypeError):
            raise HTTPException(status_code=400, detail="Invalid real_quantity value")
    
    db.commit()
    db.refresh(pt)
    return {"ok": True, "real_quantity": pt.real_quantity}
