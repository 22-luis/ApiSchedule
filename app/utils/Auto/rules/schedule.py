from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from datetime import date, time, timedelta, datetime

from app.models.programming import Programming, ProgrammingStatus, ProgrammingTask
from app.models.team import Team
from app.utils.bussiness.order_status_service import OrderStatusService
from app.services.utils.programming_utils import ProgrammingUtils

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
    def __init__(self, tolerance_minutes: int = 10):
        self.tolerance_minutes = tolerance_minutes

    def get_team_duration(self, team_name: str) -> Optional[int]:
        """Obtiene la duración para un equipo específico."""
        team_rule = TEAM_RULES.get(team_name)
        if team_rule and "duration" in team_rule:
            return team_rule["duration"]
        # Fallback a una regla por defecto si no se encuentra el equipo
        return STANDARD_DURATION_MINUTES

    def verify_programming_time_limit(self, programmings: List[Dict], task_minutes: int, db: Session, 
                                    order_data: Optional[Dict] = None, 
                                    activity_details: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Verifica límite de tiempo para programaciones.
        
        Args:
            programmings: Lista de programaciones
            task_minutes: Minutos de la tarea
            db: Sesión de base de datos
            order_data: Datos de la orden (opcional)
            activity_details: Detalles de la actividad (opcional)
            
        Returns:
            Resultado de la verificación
        """
        current_date = date.today()
        
        # Asegurar que las programaciones estén ordenadas por fecha
        sorted_programmings = sorted(
            programmings,
            key=lambda p: (
                date.fromisoformat(p.get("date", "9999-12-31")) - current_date
            ).days
        )
        
        # Evaluar cada programación secuencialmente
        for programming in sorted_programmings:
            programming_id = programming.get("id")
            programming_date = programming.get("date")
            
            # Verificar que la programación esté en fecha actual o futura
            try:
                programming_date_obj = date.fromisoformat(programming_date)
                if programming_date_obj < current_date:
                    continue
            except:
                continue
            
            # Obtener la programación completa de la base de datos
            programming_obj = db.query(Programming).filter(Programming.id == programming_id).first()
            if not programming_obj:
                continue
            
            # Verificar que la programación esté disponible
            if programming_obj.status != ProgrammingStatus.available:
                continue

            team_obj = db.query(Team).filter(Team.id == programming_obj.team_id).first()
            team_name = team_obj.name if team_obj else "Equipo desconocido"

            # Obtener duración y calcular max_allowed_minutes
            duration_minutes = self.get_team_duration(team_name)
            if duration_minutes is None:
                max_allowed_minutes = float('inf')
            else:
                max_allowed_minutes = duration_minutes + self.tolerance_minutes
            
            # Obtener las tareas de la programación
            programming_tasks = db.query(ProgrammingTask).filter(
                ProgrammingTask.programming_id == programming_id
            ).all()
            
            # Calcular el tiempo actual de la programación
            current_end_minutes = ProgrammingUtils.calculate_current_programming_time(
                programming_tasks, programming_date_obj
            )
            
            # Si la programación está vacía (current_end_minutes = 0), agregar tarea de preparación
            preparation_task_created = None
            if current_end_minutes == 0 and order_data and activity_details:
                preparation_result = self.create_preparation_task(programming_id, programming_tasks, db)
                if preparation_result.get("success"):
                    preparation_task_created = preparation_result.get("task_data")
                    # Actualizar el tiempo actual después de agregar la tarea de preparación
                    current_end_minutes = preparation_result.get("task_data", {}).get("minutes", 0) # Usar la duración de la tarea de preparación creada
                    # Recalcular las tareas de la programación
                    programming_tasks = db.query(ProgrammingTask).filter(
                        ProgrammingTask.programming_id == programming_id
                    ).all()
            
            # Calcular el tiempo final si se agrega la nueva tarea
            final_minutes = current_end_minutes + task_minutes
            
            # Verificar si se excede el límite de tiempo
            if final_minutes <= max_allowed_minutes:
                # Obtener información del equipo
                team_obj = db.query(Team).filter(Team.id == programming_obj.team_id).first()
                team_name = team_obj.name if team_obj else "Equipo desconocido"
                
                time_limit_iso = time(duration_minutes // 60, duration_minutes % 60).isoformat() if duration_minutes is not None else "No limit"

                result = {
                    "success": True,
                    "message": f"Programación seleccionada: {programming_date} - Cumple con límite de tiempo",
                    "selected_programming": {
                        "id": programming_id,
                        "date": programming_date,
                        "team_id": str(programming_obj.team_id),
                        "team_name": team_name,
                        "task_minutes": task_minutes,
                        "time_limit": time_limit_iso,
                        "tolerance_minutes": self.tolerance_minutes,
                        "current_tasks": len(programming_tasks),
                        "current_end_minutes": current_end_minutes,
                        "final_minutes": final_minutes
                    },
                    "verification_details": {
                        "current_end_minutes": current_end_minutes,
                        "final_minutes": final_minutes,
                        "max_allowed_minutes": max_allowed_minutes if max_allowed_minutes != float('inf') else "No limit",
                        "within_limit": True,
                        "programming_date": programming_date,
                        "total_existing_tasks": len(programming_tasks)
                    }
                }
                
                # Crear la tarea de la orden si se proporcionaron los datos
                if order_data and activity_details:
                    # Usar la lista actualizada de tareas (que incluye la tarea de preparación si se creó)
                    task_result = ProgrammingUtils.create_order_task(
                        programming_id, programming_tasks, task_minutes,
                        order_data, activity_details, db
                    )
                    if task_result.get("success"):
                        result["order_task_created"] = task_result.get("task_data")
                        
                        # Actualizar el estado de la orden a "programada" si la tarea se creó exitosamente
                        try:
                            # Obtener la tarea creada para actualizar el estado de la orden
                            task_id = task_result.get("task_data", {}).get("task_id")
                            if task_id:
                                from app.models.task import Task
                                task_obj = db.query(Task).filter(Task.id == task_id).first()
                                if task_obj:
                                    OrderStatusService.update_order_status_for_task_creation(db, task_obj)
                        except Exception as e:
                            # Si hay un error al actualizar el estado, no fallar la creación de la tarea
                            # Solo registrar el error en el resultado
                            result["order_status_update_error"] = str(e)
                
                # Agregar información sobre la tarea de preparación si se creó
                if preparation_task_created:
                    result["preparation_task_created"] = preparation_task_created
                    result["message"] += " (incluye tarea de preparación)"
                
                return result
            else:
                # Si se excede el límite, continuar con la siguiente programación
                continue
        
        # Si ninguna programación cumple con el límite
        return {
            "success": False,
            "message": "Ninguna programación disponible cumple con el límite de tiempo",
            "selected_programming": None,
            "evaluated_programmings": len(sorted_programmings)
        }

    def create_preparation_task(self, programming_id: str, programming_tasks: List, db: Session) -> Dict[str, Any]:
        """
        Crea una tarea de preparación cuando la programación está vacía.
        
        Args:
            programming_id: ID de la programación
            programming_tasks: Lista de tareas existentes en la programación
            db: Sesión de base de datos
            
        Returns:
            Resultado de la creación de la tarea de preparación
        """
        from app.models.programming import ProgrammingTask, Programming
        from app.models.task import Task
        from app.models.team import Team
        
        
        # Solo crear tarea de preparación si no hay tareas existentes
        if len(programming_tasks) > 0:
            return {
                "success": False,
                "message": "La programación ya tiene tareas, no se necesita tarea de preparación"
            }
        
        try:
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
                 type="PREP",
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
            db.commit()
            db.refresh(preparation_task_obj)
            db.refresh(preparation_programming_task)
            
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
            
        except Exception as e:
            db.rollback()
            return {
                "success": False,
                "message": f"Error al crear tarea de preparación: {str(e)}"
            }
