"""
Rutas de la API para cálculos de negocio centralizados.
Expone funciones de cálculo que anteriormente estaban en el frontend.
"""
from fastapi import APIRouter, Depends, HTTPException, Query, Body
from sqlalchemy.orm import Session
from app.db.dependency import get_db
from app.utils.dependencies import get_current_user, require_roles
from app.models.user import User
from app.models.role import UserRole
from app.utils.business_calculations import (
    BusinessCalculations,
    TaskDurationRequest,
    TaskDurationResponse,
    WorkingHoursRequest,
    WorkingHoursResponse
)
from datetime import date
from typing import List, Dict, Any, Optional
from pydantic import BaseModel

router = APIRouter(prefix="/calculations", tags=["calculations"])


class SequentialTimesRequest(BaseModel):
    """Esquema para solicitud de cálculo de tiempos secuenciales"""
    base_date: date
    base_time: Optional[str] = None
    tasks: List[Dict[str, Any]]


@router.post("/task-duration", response_model=TaskDurationResponse)
def calculate_task_duration(
    request: TaskDurationRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Calcula la duración de una tarea basada en cantidad, productividad y personas.
    
    Esta función centraliza la lógica de cálculo que anteriormente estaba en el frontend.
    """
    try:
        # Validar parámetros
        validation = BusinessCalculations.validate_task_parameters(
            request.quantity,
            request.productivity,
            request.people
        )
        
        if not validation['is_valid']:
            raise HTTPException(
                status_code=400,
                detail={
                    "message": "Parámetros inválidos",
                    "errors": validation['errors']
                }
            )
        
        # Calcular duración
        result = BusinessCalculations.calculate_task_duration(request)
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error calculando duración de tarea: {str(e)}"
        )


@router.get("/task-duration/simple")
def calculate_task_minutes_simple(
    quantity: int = Query(..., description="Cantidad a producir"),
    productivity: float = Query(..., description="Productividad (tiempo por unidad)"),
    people: int = Query(..., description="Número de personas"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Calcula solo los minutos de una tarea (versión simplificada).
    
    Retorna solo el número de minutos calculados.
    """
    try:
        # Validar parámetros
        validation = BusinessCalculations.validate_task_parameters(
            quantity, productivity, people
        )
        
        if not validation['is_valid']:
            raise HTTPException(
                status_code=400,
                detail={
                    "message": "Parámetros inválidos",
                    "errors": validation['errors']
                }
            )
        
        # Calcular minutos
        minutes = BusinessCalculations.calculate_task_minutes(
            quantity, productivity, people
        )
        
        return {"minutes": minutes}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error calculando minutos: {str(e)}"
        )


@router.post("/working-hours", response_model=WorkingHoursResponse)
def get_working_hours(
    request: WorkingHoursRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Obtiene las horas de trabajo para una fecha específica.
    
    Retorna las horas de inicio, fin y si es día laboral.
    """
    try:
        working_hours = BusinessCalculations.get_working_hours(request.date)
        return working_hours
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error obteniendo horas de trabajo: {str(e)}"
        )


@router.get("/working-hours/{target_date}")
def get_working_hours_by_date(
    target_date: date,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Obtiene las horas de trabajo para una fecha específica (versión GET).
    """
    try:
        working_hours = BusinessCalculations.get_working_hours(target_date)
        return working_hours
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error obteniendo horas de trabajo: {str(e)}"
        )


@router.get("/programming-base-time/{target_date}")
def get_programming_base_time(
    target_date: date,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Calcula la hora base de programación para una fecha específica.
    
    Retorna la hora base en formato ISO o null si no es día laboral.
    """
    try:
        base_time = BusinessCalculations.calculate_programming_base_time(target_date)
        
        if base_time:
            return {
                "base_time": base_time.isoformat(),
                "is_working_day": True
            }
        else:
            return {
                "base_time": None,
                "is_working_day": False
            }
            
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error calculando hora base: {str(e)}"
        )


@router.post("/sequential-times")
def calculate_sequential_times(
    request: SequentialTimesRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.PLANNER, UserRole.SUPERVISOR))
):
    """
    Calcula tiempos secuenciales para una lista de tareas.
    
    Requiere permisos de admin, planner o supervisor.
    """
    try:
        print(f"[DEBUG] Sequential times request: {request}")
        
        # Validar que las tareas tengan el campo minutes
        for task in request.tasks:
            if 'minutes' not in task:
                raise HTTPException(
                    status_code=400,
                    detail="Cada tarea debe tener el campo 'minutes'"
                )
        
        result = BusinessCalculations.calculate_sequential_times(
            request.base_date, request.tasks, request.base_time
        )
        
        print(f"[DEBUG] Sequential times result: {result}")
        
        return {
            "base_date": request.base_date.isoformat(),
            "base_time": request.base_time,
            "tasks": result
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"[DEBUG] Error in sequential times: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error calculando tiempos secuenciales: {str(e)}"
        )


@router.post("/validate-task-parameters")
def validate_task_parameters(
    quantity: int = Query(..., description="Cantidad a producir"),
    productivity: float = Query(..., description="Productividad"),
    people: int = Query(..., description="Número de personas"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Valida los parámetros de una tarea.
    
    Retorna errores de validación si los hay.
    """
    try:
        validation = BusinessCalculations.validate_task_parameters(
            quantity, productivity, people
        )
        
        return validation
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error validando parámetros: {str(e)}"
        )


@router.get("/formula-info")
def get_formula_info():
    """
    Obtiene información sobre las fórmulas de cálculo utilizadas.
    """
    return {
        "task_duration_formula": {
            "description": "Fórmula para calcular duración de tareas",
            "formula": "minutos = (cantidad × productividad × 60) ÷ personas",
            "variables": {
                "cantidad": "Número de unidades a producir",
                "productividad": "Tiempo por unidad (en horas)",
                "personas": "Número de personas asignadas",
                "minutos": "Duración calculada (redondeada hacia arriba)"
            },
            "example": {
                "cantidad": 100,
                "productividad": 0.5,
                "personas": 2,
                "resultado": "minutos = (100 × 0.5 × 60) ÷ 2 = 1500 minutos"
            }
        },
        "working_hours": {
            "description": "Horarios de trabajo configurados",
            "monday_friday": "7:00 - 17:00",
            "saturday": "7:30 - 17:30",
            "sunday": "No laboral"
        }
    }
