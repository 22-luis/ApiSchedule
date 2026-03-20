from datetime import date
from typing import List, Optional
from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session
from app.shared.db.session import get_db
from app.modules.organization.models.role import UserRole
from app.shared.utils.core.dependencies import get_current_user
from app.modules.organization.models.user import User
from app.modules.reports.repositories.report_repository import ReportRepository
from app.modules.reports.services.report_service import ReportService

router = APIRouter(prefix="/reports", tags=["reports"])

# Incluir router de compare
from app.modules.reports.api.compare import router as compare_router
router.include_router(compare_router)

# Incluir router de historico comparacion fechas
from app.modules.reports.api.historico_comparacion_fechas import router as historico_fechas_router
router.include_router(historico_fechas_router)

def get_report_service(db: Session = Depends(get_db)) -> ReportService:
    return ReportService(ReportRepository(db))

@router.get("/productivity")
async def get_productivity_report(
    start_date: date = Query(..., description="Fecha inicial del reporte"),
    end_date: date = Query(..., description="Fecha final del reporte"),
    team_id: Optional[str] = Query(None, description="ID del equipo (opcional)"),
    report_service: ReportService = Depends(get_report_service),
    current_user: User = Depends(get_current_user)
):
    """
    Genera un reporte de productividad que incluye:
    - Total de tareas programadas vs completadas
    - Tiempo total programado vs tiempo real (de record_stopwatch)
    - Cantidad programada vs cantidad real
    - Eficiencia por equipo
    """
    return report_service.get_productivity_report(start_date, end_date, team_id)

@router.get("/orders-status")
async def get_orders_status_report(
    start_date: date = Query(..., description="Fecha inicial del reporte"),
    end_date: date = Query(..., description="Fecha final del reporte"),
    report_service: ReportService = Depends(get_report_service),
    current_user: User = Depends(get_current_user)
):
    """
    Genera un reporte del estado de las órdenes que incluye:
    - Total de órdenes por estado
    - Cantidades recibidas vs programadas
    - Tiempo promedio de procesamiento
    - Órdenes atrasadas
    """
    return report_service.get_orders_status_report(start_date, end_date)

@router.get("/task-performance")
async def get_task_performance_report(
    report_service: ReportService = Depends(get_report_service),
    current_user: User = Depends(get_current_user)
):
    """
    Reporte de rendimiento por tarea con cálculos de horas y cantidades.
    Solo accesible para roles admin y accounting.
    """
    if current_user.role not in [UserRole.ADMIN, UserRole.ACCOUNTING]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permisos para acceder a este reporte. Se requiere rol admin o accounting."
        )

    return report_service.get_task_performance_report()

@router.get("/task-performance-group")
async def get_task_performance_group_report(
    year: Optional[int] = Query(None, description="Año del reporte (opcional)"),
    month: Optional[int] = Query(None, description="Mes del reporte (opcional)"),
    report_service: ReportService = Depends(get_report_service),
    current_user: User = Depends(get_current_user)
):
    """
    Reporte de rendimiento agrupado por código, descripción, tipo y personas.
    Solo accesible para roles admin y accounting.
    """
    if current_user.role not in [UserRole.ADMIN, UserRole.ACCOUNTING]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permisos para acceder a este reporte. Se requiere rol admin o accounting."
        )

    return report_service.get_task_performance_group_report(year, month)

@router.get("/team-performance")
async def get_team_performance_report(
    start_date: date = Query(..., description="Fecha inicial del reporte"),
    end_date: date = Query(..., description="Fecha final del reporte"),
    report_service: ReportService = Depends(get_report_service),
    current_user: User = Depends(get_current_user)
):
    """
    Genera un reporte de rendimiento por equipo que incluye:
    - Eficiencia en tiempo y cantidad por equipo
    - Tasa de completitud de tareas
    - Tiempo promedio por tarea
    """
    return report_service.get_team_performance_report(start_date, end_date)
