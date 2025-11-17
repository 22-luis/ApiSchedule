from datetime import datetime, date
from typing import List, Optional
from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy import func, case, and_, extract, select,cast, Float, distinct
from sqlalchemy.orm import Session, aliased
from app.db.dependency import get_db
from app.models.programming import Programming, ProgrammingTask
from app.models.task import Task
from app.models.team import Team
from app.models.order import Order
from app.models.state import ProgrammingStatus, OrderStatus
from app.models.role import UserRole
from app.models.code import Code
from app.utils.dependencies import get_current_user
from app.schemas.user import User

router = APIRouter(prefix="/reports", tags=["reports"])
performance_inverso = case(
    (Task.performance != 0, 1.0 / cast(Task.performance, Float)),
    else_=None  # Devuelve NULL si es 0
).label('performance_inverso')


@router.get("/productivity")
async def get_productivity_report(
    start_date: date = Query(..., description="Fecha inicial del reporte"),
    end_date: date = Query(..., description="Fecha final del reporte"),
    team_id: Optional[str] = Query(None, description="ID del equipo (opcional)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Genera un reporte de productividad que incluye:
    - Total de tareas programadas vs completadas
    - Tiempo total programado vs tiempo real
    - Cantidad programada vs cantidad real
    - Eficiencia por equipo
    """
    query = (
        db.query(
            Programming.date,
            Team.name.label('team_name'),
            func.count(ProgrammingTask.task_id).label('total_tasks'),
            func.sum(case([(ProgrammingTask.is_completed == True, 1)], else_=0)).label('completed_tasks'),
            func.sum(Task.minutes).label('scheduled_minutes'),
            func.sum(
                case([
                    (ProgrammingTask.real_end_time != None,
                     func.extract('epoch', ProgrammingTask.real_end_time - ProgrammingTask.real_start_time) / 60)
                ], else_=0)
            ).label('real_minutes'),
            func.sum(Task.quantity).label('scheduled_quantity'),
            func.sum(ProgrammingTask.real_quantity).label('real_quantity')
        )
        .join(Team, Programming.team_id == Team.id)
        .join(ProgrammingTask, Programming.id == ProgrammingTask.programming_id)
        .join(Task, ProgrammingTask.task_id == Task.id)
        .filter(
            Programming.date.between(start_date, end_date),
            Programming.status != ProgrammingStatus.cancelled
        )
        .group_by(Programming.date, Team.name)
        .order_by(Programming.date)
    )

    if team_id:
        query = query.filter(Team.id == team_id)

    results = query.all()
    
    return [{
        "date": row.date,
        "team_name": row.team_name,
        "total_tasks": row.total_tasks,
        "completed_tasks": row.completed_tasks,
        "completion_rate": round(row.completed_tasks / row.total_tasks * 100, 2) if row.total_tasks > 0 else 0,
        "scheduled_minutes": row.scheduled_minutes,
        "real_minutes": round(row.real_minutes, 2),
        "time_efficiency": round(row.scheduled_minutes / row.real_minutes * 100, 2) if row.real_minutes > 0 else 0,
        "scheduled_quantity": row.scheduled_quantity,
        "real_quantity": row.real_quantity,
        "quantity_efficiency": round(row.real_quantity / row.scheduled_quantity * 100, 2) if row.scheduled_quantity > 0 else 0
    } for row in results]

@router.get("/orders-status")
async def get_orders_status_report(
    start_date: date = Query(..., description="Fecha inicial del reporte"),
    end_date: date = Query(..., description="Fecha final del reporte"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Genera un reporte del estado de las órdenes que incluye:
    - Total de órdenes por estado
    - Cantidades recibidas vs programadas
    - Tiempo promedio de procesamiento
    - Órdenes atrasadas
    """
    orders_query = (
        db.query(
            Order.status,
            func.count(Order.lote).label('total_orders'),
            func.sum(Order.quantity).label('total_quantity'),
            func.sum(Order.received_quantity).label('received_quantity'),
            func.avg(
                case([
                    (Order.submitted_date != None,
                     func.extract('days', Order.submitted_date - Order.received_date))
                ], else_=None)
            ).label('avg_processing_days'),
            func.count(
                case([
                    (and_(
                        Order.status != OrderStatus.completed,
                        Order.dueDate < func.current_date()
                    ), Order.lote)
                ])
            ).label('delayed_orders')
        )
        .filter(
            Order.received_date.between(start_date, end_date)
        )
        .group_by(Order.status)
    )

    results = orders_query.all()
    
    return [{
        "status": row.status.value,
        "total_orders": row.total_orders,
        "total_quantity": row.total_quantity,
        "received_quantity": row.received_quantity,
        "completion_percentage": round(row.received_quantity / row.total_quantity * 100, 2) if row.total_quantity > 0 else 0,
        "avg_processing_days": round(row.avg_processing_days, 2) if row.avg_processing_days else 0,
        "delayed_orders": row.delayed_orders
    } for row in results]

@router.get("/task-performance")
async def get_task_performance_report(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Reporte de rendimiento por tarea con cálculos de horas y cantidades.
    Solo accesible para roles admin y accounting.

    Cálculos realizados:
    - horas: 1 / performance (rendimiento inverso) si performance != 0, None si es 0
    - total_horas: horas * cantidad_real (horas totales consumidas)
    - proporcion: (horas * cantidad_estimada) / cantidad_real si cantidad_real != 0
      Representa la relación entre horas estimadas vs reales por unidad producida
    """
    # Verificar roles permitidos
    if current_user.role not in [UserRole.ADMIN, UserRole.ACCOUNTING]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permisos para acceder a este reporte. Se requiere rol admin o accounting."
        )

    query = (
    select(
        func.date(ProgrammingTask.start_time).label('fecha'),
        Code.code,
        Code.description,
        Task.lote,
        Task.type,
        Task.activity,
        (1.0 / func.nullif(Task.performance, 0)).label('horas'),
        ProgrammingTask.real_quantity,
        (func.extract('epoch', ProgrammingTask.real_end_time - ProgrammingTask.real_start_time) / 60).label('minutes'),
        Task.people,
        ((1.0 / func.nullif(Task.performance, 0)) * ProgrammingTask.real_quantity).label('total_horas'),
        case(
            (ProgrammingTask.real_quantity != 0,
             ((1.0 / func.nullif(Task.performance, 0)) * Task.quantity) / cast(ProgrammingTask.real_quantity, Float)
            ),
            else_=None
        ).label('proporcion')
    )
    .select_from(Task)
    .join(Code, Task.code_id == Code.id)
    .join(ProgrammingTask, Task.id == ProgrammingTask.task_id)
)

    results = db.execute(query).all()

    return [{
        "fecha": row.fecha,
        "codigo": row.code,
        "descripcion": row.description,
        "lote": row.lote,
        "tipo": row.type,
        "actividad": row.activity,
        "horas": round(float(row.horas), 2) if row.horas else None,
        "cantidad_real": float(row.real_quantity) if row.real_quantity else None,
        "minutes": round(float(row.minutes), 2) if row.minutes else None,
        "personas": row.people,
        "total_horas": round(float(row.total_horas), 2) if row.total_horas else None,
        "proporcion": round(float(row.proporcion), 2) if row.proporcion else None
    } for row in results]

@router.get("/task-performance-group")
async def get_task_performance_group_report(
    year: Optional[int] = Query(None, description="Año del reporte (opcional)"),
    month: Optional[int] = Query(None, description="Mes del reporte (opcional)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Reporte de rendimiento agrupado por código, descripción, tipo y personas.
    Solo accesible para roles admin y accounting.

    Cálculos realizados:
    - Suma de total Horas (Decimal): SUM(EXTRACT(EPOCH FROM (pgt.real_end_time - pgt.real_start_time))) / 3600.0
    - Suma de cantidad por Producto: SUM(pgt.real_quantity)
    - Promedio tiempo por producto: (Suma Horas / Suma Cantidad) si Suma Cantidad != 0
    - Final: Promedio * tk.people
    """
    # Verificar roles permitidos
    if current_user.role not in [UserRole.ADMIN, UserRole.ACCOUNTING]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permisos para acceder a este reporte. Se requiere rol admin o accounting."
        )

    base_query = (
        select(
            Code.code,
            Code.description,
            Code.type,
            (func.sum(func.extract('epoch', ProgrammingTask.real_end_time - ProgrammingTask.real_start_time)) / 3600.0).label('sum_hours'),
            func.sum(ProgrammingTask.real_quantity).label('sum_quantity'),
            case(
                (func.sum(ProgrammingTask.real_quantity) != 0,
                 (func.sum(func.extract('epoch', ProgrammingTask.real_end_time - ProgrammingTask.real_start_time)) / 3600.0) / func.sum(ProgrammingTask.real_quantity)
                ),
                else_=None
            ).label('avg_time_per_product'),
            Task.people,
            case(
                (func.sum(ProgrammingTask.real_quantity) != 0,
                 ((func.sum(func.extract('epoch', ProgrammingTask.real_end_time - ProgrammingTask.real_start_time)) / 3600.0) / func.sum(ProgrammingTask.real_quantity)) * Task.people
                ),
                else_=None
            ).label('final_metric')
        )
        .select_from(Code)
        .join(Task, Code.id == Task.code_id)
        .join(ProgrammingTask, Task.id == ProgrammingTask.task_id)
    )

    if year is not None and month is not None:
        query = base_query.where(
            extract('year', ProgrammingTask.start_time) == year,
            extract('month', ProgrammingTask.start_time) == month
        ).group_by(extract('year', ProgrammingTask.start_time), extract('month', ProgrammingTask.start_time), Code.code, Code.description, Code.type, Task.people)
    else:
        query = base_query.group_by(Code.code, Code.description, Code.type, Task.people)

    results = db.execute(query).all()

    if year is not None and month is not None:
        return [{
            "year": year,
            "month": month,
            "code": row.code,
            "description": row.description,
            "type": row.type,
            "sum_hours": round(float(row.sum_hours), 4) if row.sum_hours else None,
            "sum_quantity": float(row.sum_quantity) if row.sum_quantity else None,
            "avg_time_per_product": round(float(row.avg_time_per_product), 4) if row.avg_time_per_product else None,
            "people": row.people,
            "final_metric": round(float(row.final_metric), 4) if row.final_metric else None
        } for row in results]
    else:
        return [{
            "code": row.code,
            "description": row.description,
            "type": row.type,
            "sum_hours": round(float(row.sum_hours), 4) if row.sum_hours else None,
            "sum_quantity": float(row.sum_quantity) if row.sum_quantity else None,
            "avg_time_per_product": round(float(row.avg_time_per_product), 4) if row.avg_time_per_product else None,
            "people": row.people,
            "final_metric": round(float(row.final_metric), 4) if row.final_metric else None
        } for row in results]

@router.get("/team-performance")
async def get_team_performance_report(
    start_date: date = Query(..., description="Fecha inicial del reporte"),
    end_date: date = Query(..., description="Fecha final del reporte"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Genera un reporte de rendimiento por equipo que incluye:
    - Eficiencia en tiempo y cantidad por equipo
    - Tasa de completitud de tareas
    - Tiempo promedio por tarea
    """
    team_query = (
        db.query(
            Team.name,
            func.count(distinct(Programming.id)).label('total_days'),
            func.count(ProgrammingTask.task_id).label('total_tasks'),
            func.sum(case([(ProgrammingTask.is_completed == True, 1)], else_=0)).label('completed_tasks'),
            func.sum(Task.minutes).label('scheduled_minutes'),
            func.sum(
                case([
                    (ProgrammingTask.real_end_time != None,
                     func.extract('epoch', ProgrammingTask.real_end_time - ProgrammingTask.real_start_time) / 60)
                ], else_=0)
            ).label('real_minutes'),
            func.avg(
                case([
                    (ProgrammingTask.real_end_time != None,
                     func.extract('epoch', ProgrammingTask.real_end_time - ProgrammingTask.real_start_time) / 60)
                ], else_=None)
            ).label('avg_task_minutes')
        )
        .join(Programming, Team.id == Programming.team_id)
        .join(ProgrammingTask, Programming.id == ProgrammingTask.programming_id)
        .join(Task, ProgrammingTask.task_id == Task.id)
        .filter(
            Programming.date.between(start_date, end_date),
            Programming.status != ProgrammingStatus.cancelled
        )
        .group_by(Team.name)
        .order_by(Team.name)
    )

    results = team_query.all()

    return [{
        "team_name": row.name,
        "total_days": row.total_days,
        "total_tasks": row.total_tasks,
        "completed_tasks": row.completed_tasks,
        "completion_rate": round(row.completed_tasks / row.total_tasks * 100, 2) if row.total_tasks > 0 else 0,
        "scheduled_minutes": row.scheduled_minutes,
        "real_minutes": round(row.real_minutes, 2),
        "time_efficiency": round(row.scheduled_minutes / row.real_minutes * 100, 2) if row.real_minutes > 0 else 0,
        "avg_task_minutes": round(row.avg_task_minutes, 2) if row.avg_task_minutes else 0
    } for row in results]
