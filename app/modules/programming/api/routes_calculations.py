import logging
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.shared.db.session import get_db
from app.shared.utils.core.dependencies import get_current_user, require_roles
from app.modules.core.models.user import User
from app.modules.core.models.role import UserRole
from app.shared.utils.business.business_calculations import BusinessCalculations
from app.shared.utils.core.time_utils import TimeZoneUtils
from app.modules.programming.schemas.calculations import (
    TaskDurationRequest,
    TaskDurationResponse,
    WorkingHoursResponse,
    SequentialTimesRequest,
    TaskFormValidationRequest,
    ExtraTaskValidationRequest,
    TaskEfficiencyRequest,
    TeamWorkloadRequest,
    TimeFormatRequest
)
from datetime import date
from typing import List, Dict, Any, Optional

# Configurar logger
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/calculations", tags=["calculations"])


@router.post("/task-duration", response_model=TaskDurationResponse)
def calculate_task_duration(
    request: TaskDurationRequest,
    current_user: User = Depends(get_current_user),
    simple: bool = Query(False, description="Si es verdadero, retorna solo los minutos calculados.")
):
    try:
        if simple:
            minutes = BusinessCalculations.calculate_task_minutes(
                request.quantity,
                request.productivity,
                request.people,
                request.code_people
            )
            return {"minutes": minutes, "hours": round(minutes/60, 2), "formula_used": "simple"}

        result = BusinessCalculations.calculate_task_duration(request)
        return result
        
    except Exception as e:
        logger.error(f"Error calculando duración de tarea: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error calculando duración de tarea: {e}")


@router.get("/working-hours/{target_date}", response_model=WorkingHoursResponse)
def get_working_hours_by_date(
    target_date: date,
    current_user: User = Depends(get_current_user)
):
    try:
        return BusinessCalculations.get_working_hours(target_date)
    except Exception as e:
        logger.error(f"Error obteniendo horas de trabajo: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error obteniendo horas de trabajo: {e}")


@router.get("/programming-base-time/{target_date}")
def get_programming_base_time(
    target_date: date,
    current_user: User = Depends(get_current_user)
):
    try:
        base_time = BusinessCalculations.calculate_programming_base_time(target_date)
        return {
            "base_time": base_time.isoformat() if base_time else None,
            "is_working_day": bool(base_time)
        }
    except Exception as e:
        logger.error(f"Error calculando hora base: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error calculando hora base: {e}")


@router.post("/sequential-times")
def calculate_sequential_times(
    request: SequentialTimesRequest,
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.PLANNER, UserRole.SUPERVISOR))
):
    try:
        logger.debug(f"Sequential times request: {request}")
        
        result = BusinessCalculations.calculate_sequential_times(
            request.base_date, request.tasks, request.base_time
        )
        
        return {
            "base_date": request.base_date.isoformat(),
            "base_time": request.base_time,
            "tasks": result
        }
        
    except Exception as e:
        logger.error(f"Error in sequential times: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error calculando tiempos secuenciales: {e}")


@router.post("/validate-task-parameters")
def validate_task_parameters_api(
    quantity: float = Query(..., gt=0),
    productivity: float = Query(..., gt=0),
    people: float = Query(..., gt=0),
    current_user: User = Depends(get_current_user)
):
    """Endpoint simplificado para validación de parámetros vía query."""
    return {"is_valid": True, "errors": [], "warnings": []}


@router.post("/validate-task-form")
def validate_task_form(
    request: TaskFormValidationRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Validación de formulario delegada a Pydantic en los endpoints de creación.
    Este endpoint se mantiene por compatibilidad pero con lógica simplificada.
    """
    return {"is_valid": True, "errors": [], "warnings": []}


@router.post("/validate-extra-task")
def validate_extra_task(
    request: ExtraTaskValidationRequest,
    current_user: User = Depends(get_current_user)
):
    return {"is_valid": True, "errors": [], "warnings": []}


@router.post("/task-efficiency")
def calculate_task_efficiency(
    request: TaskEfficiencyRequest,
    current_user: User = Depends(get_current_user)
):
    try:
        return BusinessCalculations.calculate_task_efficiency(
            request.planned_minutes,
            request.actual_minutes
        )
    except Exception as e:
        logger.error(f"Error calculando eficiencia: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error calculando eficiencia: {e}")

@router.post("/team-workload")
def calculate_team_workload(
    request: TeamWorkloadRequest,
    current_user: User = Depends(get_current_user)
):
    try:
        return BusinessCalculations.calculate_team_workload(
            request.tasks,
            request.working_hours
        )
    except Exception as e:
        logger.error(f"Error calculando carga de trabajo: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error calculando carga de trabajo: {e}")

@router.post("/format-time")
def format_time(
    request: TimeFormatRequest,
    current_user: User = Depends(get_current_user)
):
    try:
        formatted_time = TimeZoneUtils.format_time_el_salvador(request.time_str)
        return {
            "formatted_time": formatted_time,
            "original_time": request.time_str,
            "timezone": "America/El_Salvador"
        }
    except Exception as e:
        logger.error(f"Error formateando tiempo: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error formateando tiempo: {e}")

@router.get("/programming-base-time-utc/{target_date}")
def get_programming_base_time_utc(
    target_date: date,
    current_user: User = Depends(get_current_user)
):
    try:
        base_time_utc = TimeZoneUtils.get_programming_base_time_utc(target_date)
        if base_time_utc:
            return {
                "base_time_utc": base_time_utc.isoformat(),
                "is_working_day": True,
                "el_salvador_time": TimeZoneUtils.format_time_el_salvador(base_time_utc.isoformat())
            }
        else:
            return {
                "base_time_utc": None,
                "is_working_day": False,
                "el_salvador_time": None
            }
    except Exception as e:
        logger.error(f"Error calculando hora base UTC: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error calculando hora base UTC: {e}")
