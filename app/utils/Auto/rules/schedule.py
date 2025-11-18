import requests
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from datetime import date, time, timedelta, datetime

from app.models.programming import Programming, ProgrammingStatus, ProgrammingTask
from app.models.team import Team
from app.utils.business.order_status_service import OrderStatusService
from app.services.utils.programming_utils import ProgrammingUtils
from app.models.task import Task

# Duración estándar de la programación en minutos
STANDARD_DURATION_MINUTES = 460

# Reglas de equipos
# 'duration': duración máxima en minutos. None significa sin límite.
TEAM_RULES = {
    "Molino": {
        "duration": STANDARD_DURATION_MINUTES
    },
    "Pesado": {
        "duration": None  # Sin límite de duración estándar
    },
    "Fabricado 1": {
        "duration": STANDARD_DURATION_MINUTES
    },
    "Fabricado 2": {
        "duration": STANDARD_DURATION_MINUTES
    },
    "Fabricado 3": {
        "duration": STANDARD_DURATION_MINUTES
    },
    "Empaque 1": {
        "duration": STANDARD_DURATION_MINUTES
    },
    "Empaque 2": {
        "duration": STANDARD_DURATION_MINUTES
    },
    "Empaque 3": {
        "duration": STANDARD_DURATION_MINUTES
    },
    "Empaque 4": {
        "duration": STANDARD_DURATION_MINUTES
    },
    "Maquina 1": {
        "duration": STANDARD_DURATION_MINUTES
    },
    "Maquina 2": {
        "duration": STANDARD_DURATION_MINUTES
    }
}

class ScheduleRule:
    def __init__(self, tolerance_minutes: int = 10, time_limit: Optional[time] = None):
        self.tolerance_minutes = tolerance_minutes
        self.time_limit = time_limit

    def get_team_duration(self, team_name: str) -> Optional[int]:
        """Obtiene la duración para un equipo específico."""
        team_rule = TEAM_RULES.get(team_name)
        if team_rule and "duration" in team_rule:
            return team_rule["duration"]
        # Fallback a una regla por defecto si no se encuentra el equipo
        return STANDARD_DURATION_MINUTES

    def verify_programming_time_limit(self, team_id: str, task_minutes: int, db: Session,
                                    order_data: Optional[Dict] = None,
                                    activity_details: Optional[Dict] = None,
                                    start_date: Optional[date] = None) -> Dict[str, Any]:
        """
        Finds a suitable programming and creates a task.
        """

        team = db.query(Team).filter(Team.id == team_id).first()
        max_duration = self.get_team_duration(team.name if team else "")

        available_programmings = ProgrammingUtils.get_available_programmings_for_team(
            team_id, db
        )

        selected_programming_data = None
        if available_programmings:
            for programming_data in available_programmings:
                if max_duration is None:
                    selected_programming_data = programming_data
                    break

                programming_id = programming_data["id"]
                programming_obj = db.query(Programming).filter(Programming.id == programming_id).first()
                if not programming_obj:
                    continue

                current_minutes = ProgrammingUtils.calculate_current_programming_time(
                    programming_obj.programming_tasks, programming_obj.date
                )

                if current_minutes + task_minutes <= max_duration:
                    selected_programming_data = programming_data
                    break
        
        if not selected_programming_data:
            return {
                "success": False,
                "message": "No se encontró una programación disponible con tiempo suficiente.",
                "selected_programming": None,
            }

        programming_id = selected_programming_data["id"]
        programming_obj = db.query(Programming).filter(Programming.id == programming_id).first()
        programming_tasks = db.query(ProgrammingTask).filter(
            ProgrammingTask.programming_id == programming_id
        ).all()

        # If programming is empty, create preparation task
        preparation_task_created = None
        if not programming_tasks and order_data and activity_details:
            preparation_result = self.create_preparation_task(programming_id, programming_tasks, db)
            if preparation_result.get("success"):
                preparation_task_created = preparation_result.get("task_data")
                # Refresh tasks
                programming_tasks = db.query(ProgrammingTask).filter(
                    ProgrammingTask.programming_id == programming_id
                ).all()

        # Create the actual task
        task_result = ProgrammingUtils.create_order_task(
            programming_id, programming_tasks, task_minutes,
            order_data, activity_details, db
        )

        if not task_result.get("success"):
            return {
                "success": False,
                "message": "Error al crear la tarea en la programación seleccionada",
                "selected_programming": selected_programming_data,
            }

        result = {
            "success": True,
            "message": f"Programación seleccionada: {selected_programming_data['date']}",
            "selected_programming": selected_programming_data,
            "order_task_created": task_result.get("task_data"),
        }

        if preparation_task_created:
            result["preparation_task_created"] = preparation_task_created
            result["message"] += " (incluye tarea de preparación)"

        # Update order status
        try:
            task_id = task_result.get("task_data", {}).get("task_id")
            if task_id:
                task_obj = db.query(Task).filter(Task.id == task_id).first()
                if task_obj:
                    OrderStatusService.update_order_status_for_task_creation(db, task_obj)
        except Exception as e:
            result["order_status_update_error"] = str(e)

        return result

    def create_preparation_task(self, programming_id: str, programming_tasks: List, db: Session) -> Dict[str, Any]:

        # Solo crear tarea de preparación si no hay tareas existentes
        if len(programming_tasks) > 0:
            return {
                "success": False,
                "message": "La programación ya tiene tareas, no se necesita tarea de preparación"
            }
        
        # Obtener la fecha de la programación
        programming_obj = db.query(Programming).filter(Programming.id == programming_id).first()
        programming_date = programming_obj.date if programming_obj else date.today()
        
        # Obtener el equipo para determinar la duración de preparación
        team_obj = None
        if programming_obj and programming_obj.team_id:
            team_obj = db.query(Team).filter(Team.id == programming_obj.team_id).first()
        
        preparation_duration = 10
        
        # Crear datetime para start_time usando la fecha de la programación
        task_start_time = datetime.combine(programming_date, time(7, 0))  # 07:00
        task_end_time = datetime.combine(programming_date, time(7, 0)) + timedelta(minutes=preparation_duration)
        
        # Crear la tarea de preparación (objeto Task)
        preparation_task_obj = Task(
             code_id=None,  # No hay código específico para preparación
             lote=None,
             quantity=None,
             specification=None,
             people=None,
             performance=None,
             material=None,
             presentation=None,
             fabricationCode=None,
             usefulLife=None,
             unit=None,
             type=None,
             activity="REUNION Y PREPARACION DE AREA",
             description="REUNION Y PREPARACION DE AREA",
             minutes=preparation_duration,
             start_time=task_start_time,
             end_time=task_end_time
         )
        
        # Obtener el número de orden para la nueva tarea
        new_task_order = len(programming_tasks) + 1
        
        # Crear la asociación con la programación
        preparation_programming_task = ProgrammingTask(
            programming_id=programming_id,
            task_id=preparation_task_obj.id,
            order=new_task_order,
            start_time=task_start_time,
            end_time=task_end_time
        )
        
        # Agregar la tarea a la base de datos
        db.add(preparation_task_obj)
        db.flush()
        preparation_programming_task.task_id = preparation_task_obj.id
        db.add(preparation_programming_task)
        
        team_name = team_obj.name if team_obj else "Equipo desconocido"
        
        return {
            "success": True,
             "message": f"Tarea de preparación creada exitosamente (duración: {preparation_duration} minutos)",
             "task_data": {
                 "task_id": str(preparation_task_obj.id),
                 "programming_id": str(preparation_programming_task.programming_id),
                 "order": new_task_order,
                 "start_time": task_start_time.isoformat(),
                 "end_time": task_end_time.isoformat(),
                 "minutes": preparation_duration,
                 "description": preparation_task_obj.description,
                 "team_name": team_name
             }
         }