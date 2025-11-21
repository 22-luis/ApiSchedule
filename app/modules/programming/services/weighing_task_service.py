"""
Servicio refactorizado para manejar la creación de tareas de pesado.
Hereda de BaseTaskService para reutilizar funcionalidad común.
"""

from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from datetime import time
import math

from app.modules.programming.services.base_task_service import BaseTaskService
from app.modules.programming.services.config import ServiceType, ServiceConfig
from app.shared.utils.Auto.rules.weighning import WeighingRule


class WeighingTaskService(BaseTaskService):
    """Servicio para manejar la creación de tareas de pesado"""
    
    def __init__(self):
        """Inicializa el servicio de pesado con límite de tiempo específico"""
        # Usar configuración centralizada
        time_limit = ServiceConfig.get_time_limit(ServiceType.WEIGHING)
        tolerance_minutes = ServiceConfig.get_tolerance_minutes(ServiceType.WEIGHING)
        super().__init__(time_limit=time_limit, tolerance_minutes=tolerance_minutes)
        self.weighing_rule = WeighingRule()
    
    def filter_activities(self, activities_data: Dict[str, Any]) -> Dict[str, Any]:
        return self.weighing_rule.filter_activities(activities_data)
    
    def get_most_suitable_team(self, db: Session) -> Dict[str, Any]:
        return self.weighing_rule.get_most_suitable_team(db)
    
    def get_activity_for_order(self, order_data: Dict, activities_data: Dict) -> Optional[Dict]:
        return self.weighing_rule.get_activity_for_order(order_data, activities_data)
    
    def get_weighing_activities_with_minutes(self, extracted_orders: List[Dict], db: Session) -> Dict[str, Any]:
        """
        Obtiene las actividades de pesado para todas las órdenes extraídas y calcula los minutos.
        
        Args:
            extracted_orders: Lista de órdenes extraídas (con lote, quantity, code)
            db: Sesión de base de datos
            
        Returns:
            Diccionario con actividades de pesado y minutos calculados
        """
        # Obtener todas las actividades
        all_activities = self.get_activities_for_orders(extracted_orders, db)
        
        # Filtrar solo las de pesado
        weighing_activities = self.filter_activities(all_activities)
        
        # Calcular minutos para cada actividad de pesado
        weighing_activities_with_minutes = {}
        weighing_activities_by_code = weighing_activities.get("weighing_activities_by_code", {})
        
        for code, code_data in weighing_activities_by_code.items():
            weighing_activities_list = code_data.get("weighing_activities", [])
            activities_with_minutes = []
            
            for activity_data in weighing_activities_list:
                activity_name = activity_data.get("activity")
                if activity_name:
                    # Buscar la cantidad de la orden correspondiente
                    order_quantity = None
                    for order in extracted_orders:
                        if order.get("code") == code:
                            order_quantity = order.get("quantity")
                            break
                    
                    if order_quantity is not None:
                        # Calcular minutos
                        performance = activity_data.get("performance")
                        time = activity_data.get("time")
                        calculated_minutes = self.calculate_minutes_from_performance_and_quantity(
                            performance, order_quantity, time
                        )
                        
                        # Calcular horas para mostrar en la fórmula
                        if performance:
                            # performance = unidades por hora -> hours = quantity * (1/performance)
                            try:
                                hours_calc = order_quantity * (1.0 / performance) if performance != 0 else 0
                                hours_calculation = hours_calc
                                formula = f"{order_quantity} / {performance} = {hours_calculation} horas * 60 = {calculated_minutes} minutos (con ceiling)"
                            except Exception:
                                hours_calculation = 0
                                formula = f"Error calculando fórmula: performance={performance}, quantity={order_quantity}"
                        elif time:
                            hours_calculation = 0  # Para tiempo directo, no hay cálculo de horas
                            formula = f"Tiempo directo: {time} minutos = {calculated_minutes} minutos (con ceiling)"
                        else:
                            hours_calculation = 0
                            formula = f"Valor por defecto: {calculated_minutes} minutos"
                        
                        activities_with_minutes.append({
                            "activity_data": activity_data,
                            "minutes_calculation": {
                                "performance": performance,
                                "time": time,
                                "quantity": order_quantity,
                                "hours_calculation": hours_calculation,
                                "calculated_minutes": calculated_minutes,
                                "formula": formula
                            }
                        })
            
            if activities_with_minutes:
                weighing_activities_with_minutes[code] = {
                    "code": code,
                    "weighing_activities_with_minutes": activities_with_minutes,
                    "total_weighing_activities": len(activities_with_minutes),
                    "found": True
                }
        
        return {
            "all_activities": all_activities,
            "weighing_activities": weighing_activities,
            "weighing_activities_with_minutes": {
                "weighing_activities_with_minutes_by_code": weighing_activities_with_minutes,
                "total_codes_with_weighing_minutes": len(weighing_activities_with_minutes),
                "codes_with_weighing_minutes": list(weighing_activities_with_minutes.keys())
            },
            "total_orders_processed": len(extracted_orders)
        }
    
    def create_weighing_tasks_for_orders(self, extracted_orders: List[Dict], db: Session) -> Dict[str, Any]:
        """
        Función principal que maneja todo el proceso de creación de tareas de pesado.
        Utiliza la implementación base de create_tasks_for_orders pero con actividades que incluyen minutos calculados.
        
        Args:
            extracted_orders: Lista de órdenes extraídas con lote, quantity y code
            db: Sesión de base de datos
        
        Returns:
            Resultado del proceso con información de las tareas creadas
        """
        try:
            # Obtener actividades con minutos calculados
            activities_with_minutes = self.get_weighing_activities_with_minutes(extracted_orders, db)
            
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
            
            weighing_activities_with_minutes = activities_with_minutes.get("weighing_activities_with_minutes", {}).get("weighing_activities_with_minutes_by_code", {})
            
            for order_data in extracted_orders:
                order_code = order_data.get('code')
                
                # Obtener la actividad con minutos calculados para esta orden
                code_activities = weighing_activities_with_minutes.get(order_code, {}).get("weighing_activities_with_minutes", [])
                
                if not code_activities:
                    failed_orders.append({
                        "order_data": order_data,
                        "reason": "No se encontró actividad válida"
                    })
                    continue
                
                # Usar la primera actividad (que debería ser la de pesado)
                activity_with_minutes = code_activities[0]
                task_minutes = activity_with_minutes.get("minutes_calculation", {}).get("calculated_minutes", 0)
                activity_details = activity_with_minutes.get("activity_data", {})
                
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
                "activities_data": activities_with_minutes.get("weighing_activities")
            }
            
        except Exception as e:
            # Log a more detailed error message, including traceback
            import traceback
            print(f"Error during weighing task creation: {str(e)}\n{traceback.format_exc()}")
            
            # Rollback the transaction to avoid inconsistent state
            db.rollback()
            
            # Re-raise the exception so it's not silent
            raise
