import logging
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.shared.db.session import get_db
from app.shared.utils.core.dependencies import get_current_user, require_roles
from app.modules.core.models.user import User
from app.modules.core.models.role import UserRole
from app.shared.utils.business.business_calculations import (
    BusinessCalculations,
    TimeZoneUtils,
    TaskDurationRequest,
    WorkingHoursResponse
)
from datetime import date
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Extra

# Configurar logger
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/calculations", tags=["calculations"])

class TaskWithMinutes(BaseModel):
    minutes: int

    class Config:
        extra = Extra.allow 


class SequentialTimesRequest(BaseModel):
    base_date: date
    base_time: Optional[str] = None
    tasks: List[TaskWithMinutes]


@router.post("/task-duration")
def calculate_task_duration(
    request: TaskDurationRequest,
    current_user: User = Depends(get_current_user),
    simple: bool = Query(False, description="Si es verdadero, retorna solo los minutos calculados.")
):
    try:
        validation = BusinessCalculations.validate_task_parameters(
            request.quantity,
            request.productivity,
            request.people
        )
        
        if not validation['is_valid']:
            raise HTTPException(
                status_code=400,
                detail={"message": "Parámetros inválidos", "errors": validation['errors']}
            )
        
        if simple:
            minutes = BusinessCalculations.calculate_task_minutes(
                request.quantity,
                request.productivity,
                request.people,
                request.code_people
            )
            return {"minutes": minutes}

        result = BusinessCalculations.calculate_task_duration(request)
        return result
        
    except HTTPException:
        raise
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
        
        # La validación de `minutes` ahora es manejada por Pydantic en el modelo SequentialTimesRequest
        result = BusinessCalculations.calculate_sequential_times(
            request.base_date, request.tasks, request.base_time
        )
        
        logger.debug(f"Sequential times result: {result}")
        
        return {
            "base_date": request.base_date.isoformat(),
            "base_time": request.base_time,
            "tasks": result
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in sequential times: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error calculando tiempos secuenciales: {e}")


@router.post("/validate-task-parameters")
def validate_task_parameters(
    quantity: int = Query(..., description="Cantidad a producir"),
    productivity: float = Query(..., description="Productividad"),
    people: int = Query(..., description="Número de personas"),
    current_user: User = Depends(get_current_user)
):
    try:
        return BusinessCalculations.validate_task_parameters(quantity, productivity, people)
    except Exception as e:
        logger.error(f"Error validando parámetros: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error validando parámetros: {e}")

class TaskFormValidationRequest(BaseModel):
    form_data: Dict[str, Any]

class ExtraTaskValidationRequest(BaseModel):
    description: str
    minutes: str
    selected_team: str
    programming_id: str

class TaskEfficiencyRequest(BaseModel):
    planned_minutes: int
    actual_minutes: int

class TeamWorkloadRequest(BaseModel):
    tasks: List[Dict[str, Any]]
    working_hours: int = 8

class TimeFormatRequest(BaseModel):
    time_str: str


@router.post("/validate-task-form")
def validate_task_form(
    request: TaskFormValidationRequest,
    current_user: User = Depends(get_current_user)
):
    try:
        return BusinessCalculations.validate_task_form_data(request.form_data)
    except Exception as e:
        logger.error(f"Error validando formulario: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error validando formulario: {e}")

@router.post("/validate-extra-task")
def validate_extra_task(
    request: ExtraTaskValidationRequest,
    current_user: User = Depends(get_current_user)
):
    try:
        return BusinessCalculations.validate_extra_task_data(
            request.description,
            request.minutes,
            request.selected_team,
            request.programming_id
        )
    except Exception as e:
        logger.error(f"Error validando tarea extra: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error validando tarea extra: {e}")

# puede usarse luego
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
        # Actualmente, formatea específicamente a la zona de El Salvador.
        formatted_time = TimeZoneUtils.format_time_el_salvador(request.time_str)
        return {
            "formatted_time": formatted_time,
            "original_time": request.time_str,
            "timezone": "America/El_Salvador"  # Devolver la zona horaria usada
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
