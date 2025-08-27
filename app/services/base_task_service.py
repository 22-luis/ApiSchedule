"""
Clase base abstracta para servicios de tareas.
Define la interfaz común que deben implementar todos los servicios de tareas.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from datetime import time, timedelta
import math

from app.services.utils.programming_utils import ProgrammingUtils
from app.utils.order_status_service import OrderStatusService
from app.core.task_config import get_reunion_preparacion_duration


class BaseTaskService(ABC):
    """Clase base abstracta para servicios de tareas"""
    
    def __init__(self, time_limit: time, tolerance_minutes: int = 5):
        """
        Inicializa el servicio base con configuración de tiempo.
        
        Args:
            time_limit: Límite de tiempo para las tareas
            tolerance_minutes: Minutos de tolerancia adicionales
        """
        self.time_limit = time_limit
        self.tolerance_minutes = tolerance_minutes
        self.max_allowed_minutes = time_limit.hour * 60 + time_limit.minute + tolerance_minutes
    
    @abstractmethod
    def filter_activities(self, activities_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Filtra las actividades específicas del servicio.
        
        Args:
            activities_data: Datos de todas las actividades
            
        Returns:
            Actividades filtradas específicas del servicio
        """
        pass
    
    @abstractmethod
    def get_most_suitable_team(self, db: Session) -> Dict[str, Any]:
        """
        Obtiene el equipo más idóneo para el tipo de tarea.
        
        Args:
            db: Sesión de base de datos
            
        Returns:
            Información del equipo más idóneo
        """
        pass
    
    @abstractmethod
    def get_activity_for_order(self, order_data: Dict, activities_data: Dict) -> Optional[Dict]:
        """
        Obtiene la actividad específica para una orden.
        
        Args:
            order_data: Datos de la orden
            activities_data: Datos de actividades filtradas
            
        Returns:
            Actividad específica para la orden o None
        """
        pass
    
    def extract_order_data(self, orders: List) -> List[Dict[str, Any]]:
        """
        Extrae datos de órdenes usando las utilidades comunes.
        
        Args:
            orders: Lista de objetos Order
            
        Returns:
            Lista de diccionarios con datos extraídos
        """
        return ProgrammingUtils.extract_order_data(orders)
    
    def get_activities_by_code(self, code: str, db: Session) -> Dict[str, Any]:
        """
        Obtiene actividades por código usando las utilidades comunes.
        
        Args:
            code: Código de la orden
            db: Sesión de base de datos
            
        Returns:
            Actividades del código
        """
        return ProgrammingUtils.get_activities_by_code(code, db)
    
    def get_activities_for_orders(self, extracted_orders: List[Dict], db: Session) -> Dict[str, Any]:
        """
        Obtiene actividades para órdenes usando las utilidades comunes.
        
        Args:
            extracted_orders: Órdenes extraídas
            db: Sesión de base de datos
            
        Returns:
            Actividades organizadas por código
        """
        return ProgrammingUtils.get_activities_for_orders(extracted_orders, db)
    
    def get_activity_details_by_code_and_activity(self, code: str, activity: str, db: Session) -> Dict[str, Any]:
        """
        Obtiene detalles de actividad usando las utilidades comunes.
        
        Args:
            code: Código del producto
            activity: Nombre de la actividad
            db: Sesión de base de datos
            
        Returns:
            Detalles de la actividad
        """
        return ProgrammingUtils.get_activity_details_by_code_and_activity(code, activity, db)
    
    def get_available_programmings_for_team(self, team_id: str, db: Session) -> List[Dict[str, Any]]:
        """
        Obtiene programaciones disponibles usando las utilidades comunes.
        
        Args:
            team_id: ID del equipo
            db: Sesión de base de datos
            
        Returns:
            Lista de programaciones disponibles
        """
        return ProgrammingUtils.get_available_programmings_for_team(team_id, db)
    
    def get_service_config(self) -> Dict[str, Any]:
        """
        Obtiene la configuración del servicio.
        
        Returns:
            Diccionario con la configuración del servicio
        """
        from app.services.config import ServiceConfig
        service_type = self.__class__.__name__.replace('TaskService', '').upper()
        
        # Mapear nombres de clase a tipos de servicio
        service_type_mapping = {
            'WEIGHING': 'WEIGHING',
            'FABRICATION': 'FABRICACION',
            'PACKAGING': 'PACKAGING'
        }
        
        config_type = service_type_mapping.get(service_type, service_type)
        
        try:
            config = ServiceConfig.CONFIGURATIONS.get(config_type, {})
            return {
                "description": config.get("description", "Servicio de tareas"),
                "time_limit": self.time_limit,
                "tolerance_minutes": self.tolerance_minutes,
                "activity_keywords": config.get("activity_keywords", []),
                "team_priorities": config.get("team_priorities", [])
            }
        except Exception:
            return {
                "description": "Servicio de tareas",
                "time_limit": self.time_limit,
                "tolerance_minutes": self.tolerance_minutes,
                "activity_keywords": [],
                "team_priorities": []
            }
    
    def calculate_minutes_from_performance_and_quantity(self, performance: float, quantity: int, time: float = None) -> int:
        """
        Calcula minutos basándose en performance y cantidad.
        
        Args:
            performance: Rendimiento en horas
            quantity: Cantidad de la orden
            time: Tiempo base en minutos (alternativa a performance)
            
        Returns:
            Minutos calculados
        """
        if quantity is None:
            return 0
        
        if performance is not None:
            # Usar performance si está disponible
            hours = performance * quantity
            minutes = hours * 60
            return math.ceil(minutes)
        elif time is not None:
            # Usar time directamente como minutos
            return math.ceil(time)
        else:
            # Valor por defecto
            return 30
    
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
        from datetime import datetime, date, time
        from app.core.task_config import get_reunion_preparacion_duration
        
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
            
            # Obtener la duración de preparación según el equipo
            team_name = team_obj.name if team_obj else "default"
            preparation_duration = get_reunion_preparacion_duration(team_name)
            
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
        from datetime import date
        from app.models.programming import Programming, ProgrammingStatus
        from app.models.programming import ProgrammingTask
        from app.models.team import Team
        
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
            if final_minutes <= self.max_allowed_minutes:
                # Obtener información del equipo
                team_obj = db.query(Team).filter(Team.id == programming_obj.team_id).first()
                team_name = team_obj.name if team_obj else "Equipo desconocido"
                
                result = {
                    "success": True,
                    "message": f"Programación seleccionada: {programming_date} - Cumple con límite de tiempo",
                    "selected_programming": {
                        "id": programming_id,
                        "date": programming_date,
                        "team_id": str(programming_obj.team_id),
                        "team_name": team_name,
                        "task_minutes": task_minutes,
                        "time_limit": self.time_limit.isoformat(),
                        "tolerance_minutes": self.tolerance_minutes,
                        "current_tasks": len(programming_tasks),
                        "current_end_minutes": current_end_minutes,
                        "final_minutes": final_minutes
                    },
                    "verification_details": {
                        "current_end_minutes": current_end_minutes,
                        "final_minutes": final_minutes,
                        "max_allowed_minutes": self.max_allowed_minutes,
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
    
    def create_tasks_for_orders(self, extracted_orders: List[Dict], db: Session) -> Dict[str, Any]:
        """
        Función principal que maneja todo el proceso de creación de tareas.
        
        Args:
            extracted_orders: Lista de órdenes extraídas
            db: Sesión de base de datos
        
        Returns:
            Resultado del proceso con información de las tareas creadas
        """
        try:
            # Obtener actividades con minutos calculados
            activities_data = self.get_activities_for_orders(extracted_orders, db)
            filtered_activities = self.filter_activities(activities_data)
            
            # Obtener equipo más idóneo
            team_result = self.get_most_suitable_team(db)
            
            if not team_result.get("success"):
                return {
                    "success": False,
                    "message": "No se pudo obtener equipo idóneo",
                    "tasks_created": 0,
                    "total_orders": len(extracted_orders)
                }
            
            team_id = team_result.get("most_suitable_team", {}).get("id")
            if not team_id:
                return {
                    "success": False,
                    "message": "ID del equipo no válido",
                    "tasks_created": 0,
                    "total_orders": len(extracted_orders)
                }
            
            # Obtener programaciones disponibles
            available_programmings = self.get_available_programmings_for_team(team_id, db)
            
            if not available_programmings:
                return {
                    "success": False,
                    "message": "No se encontraron programaciones disponibles",
                    "tasks_created": 0,
                    "total_orders": len(extracted_orders)
                }
            
            # Procesar cada orden
            created_tasks = []
            failed_orders = []
            
            for order_data in extracted_orders:
                # Obtener la actividad específica para esta orden
                activity = self.get_activity_for_order(order_data, filtered_activities)
                
                if not activity:
                    failed_orders.append({
                        "order_data": order_data,
                        "reason": "No se encontró actividad válida"
                    })
                    continue
                
                task_minutes = activity.get("minutes_calculation", {}).get("calculated_minutes", 0)
                activity_details = activity.get("activity_data", {})
                
                if task_minutes <= 0:
                    failed_orders.append({
                        "order_data": order_data,
                        "reason": "Los minutos calculados no son válidos"
                    })
                    continue
                
                # Verificar límite de tiempo y crear tarea
                time_verification = self.verify_programming_time_limit(
                    available_programmings, task_minutes, db, order_data, activity_details
                )
                
                if time_verification.get("success") and time_verification.get("order_task_created"):
                    created_tasks.append({
                        "order_data": order_data,
                        "selected_programming": time_verification.get("selected_programming"),
                        "order_task": time_verification.get("order_task_created")
                    })
                else:
                    failed_orders.append({
                        "order_data": order_data,
                        "reason": time_verification.get("message", "Error desconocido")
                    })
            
            return {
                "success": True,
                "message": f"Procesamiento completado. {len(created_tasks)} tareas creadas de {len(extracted_orders)} órdenes",
                "tasks_created": len(created_tasks),
                "total_orders": len(extracted_orders),
                "created_tasks": created_tasks,
                "failed_orders": failed_orders,
                "team_data": team_result.get("most_suitable_team"),
                "activities_data": filtered_activities
            }
            
        except Exception as e:
            return {
                "success": False,
                "message": f"Error durante la creación de tareas: {str(e)}",
                "tasks_created": 0,
                "total_orders": len(extracted_orders)
            }
