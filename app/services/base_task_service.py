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
from app.utils.business.order_status_service import OrderStatusService
from app.utils.Auto.rules.schedule import ScheduleRule


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
        self.schedule_rule = ScheduleRule(time_limit, tolerance_minutes)
    
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
        return self.schedule_rule.create_preparation_task(programming_id, programming_tasks, db)
    
    def verify_programming_time_limit(self, programmings: List[Dict], task_minutes: int, db: Session, 
                                    order_data: Optional[Dict] = None, 
                                    activity_details: Optional[Dict] = None) -> Dict[str, Any]:
        return self.schedule_rule.verify_programming_time_limit(programmings, task_minutes, db, order_data, activity_details)
    
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
