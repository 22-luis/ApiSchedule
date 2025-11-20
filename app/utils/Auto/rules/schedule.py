from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from datetime import date, time, timedelta, datetime

from app.models.programming import Programming, ProgrammingStatus, ProgrammingTask
from app.models.team import Team
from app.utils.business.order_status_service import OrderStatusService
from app.services.utils.programming_utils import ProgrammingUtils
from app.models.task import Task
from app.utils.core.logging import get_logger
from app.utils.business.programming_availability import get_programming_availability, TEAM_RULES, STANDARD_DURATION_MINUTES

logger = get_logger(__name__)

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
        
        logger.debug(f"Iniciando verificación de {len(sorted_programmings)} programaciones para una tarea de {task_minutes} minutos.")

        # Evaluar cada programación secuencialmente
        for programming in sorted_programmings:
            programming_id = programming.get("id")
            programming_date = programming.get("date")
            
            logger.debug(f"Evaluando programación ID: {programming_id} con fecha: {programming_date}")

            # Verificar que la programación esté en fecha actual o futura
            try:
                programming_date_obj = date.fromisoformat(programming_date)
                if programming_date_obj < current_date:
                    logger.debug(f"Descartada {programming_id}: La fecha {programming_date} es anterior a la actual {current_date}.")
                    continue
            except:
                logger.warning(f"Descartada {programming_id}: Formato de fecha inválido '{programming_date}'.")
                continue
            
            # Obtener la programación completa de la base de datos
            programming_obj = db.query(Programming).filter(Programming.id == programming_id).first()
            if not programming_obj:
                logger.warning(f"Descartada {programming_id}: No se encontró en la base de datos.")
                continue
            
            # Verificar que la programación esté disponible
            if programming_obj.status != ProgrammingStatus.available:
                logger.debug(f"Descartada {programming_id}: Estado no es 'available' (es '{programming_obj.status}').")
                continue

            # Verificar disponibilidad usando la nueva función centralizada
            availability_result = get_programming_availability(db, str(programming_id), task_minutes)
            
            if availability_result["available"]:
                # Obtener datos del resultado
                current_end_minutes = availability_result["current_end_minutes"]
                final_minutes = availability_result["final_minutes"]
                max_allowed_minutes = availability_result["max_allowed_minutes"]
                team_name = availability_result["team_name"]
                
                # Recalcular duration_minutes para el log (inverso de max_allowed)
                duration_minutes = None
                if max_allowed_minutes != float('inf'):
                    duration_minutes = max_allowed_minutes - self.tolerance_minutes

                time_limit_iso = "No limit"
                if duration_minutes is not None:
                    # Convertir a int de forma segura
                    dm_int = int(duration_minutes)
                    time_limit_iso = time(dm_int // 60, dm_int % 60).isoformat()

                logger.info(f"Programación {programming_id} seleccionada. Final: {final_minutes} <= Máx: {max_allowed_minutes}.")
                
                # Obtener las tareas de la programación para el reporte (y creación de tarea)
                programming_tasks = db.query(ProgrammingTask).filter(
                    ProgrammingTask.programming_id == programming_id
                ).all()

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
                                task_obj = db.query(Task).filter(Task.id == task_id).first()
                                if task_obj:
                                    OrderStatusService.update_order_status_for_task_creation(db, task_obj)
                        except Exception as e:
                            # Si hay un error al actualizar el estado, no fallar la creación de la tarea
                            # Solo registrar el error en el resultado
                            result["order_status_update_error"] = str(e)

                return result
            else:
                logger.debug(f"Descartada {programming_id}: Excede el límite de tiempo. Final: {availability_result['final_minutes']} > Máx: {availability_result['max_allowed_minutes']}.")
                # Si se excede el límite, continuar con la siguiente programación
                continue
        
        logger.warning("No se encontró ninguna programación que cumpla con los requisitos.")
        # Si ninguna programación cumple con el límite
        return {
            "success": False,
            "message": "Ninguna programación disponible cumple con el límite de tiempo",
            "selected_programming": None,
            "evaluated_programmings": len(sorted_programmings)
        }