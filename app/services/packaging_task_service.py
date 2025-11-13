"""
Servicio refactorizado para manejar la creación de tareas de empaque.
Hereda de BaseTaskService para reutilizar funcionalidad común.
"""

from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from datetime import time
import math

from app.services.base_task_service import BaseTaskService
from app.services.config import ServiceType, ServiceConfig
from app.utils.Auto.rules.packaging import PackagingRule


class PackagingTaskService(BaseTaskService):
    """Servicio para manejar la creación de tareas de empaque"""
    
    def __init__(self):
        """Inicializa el servicio de empaque con límite de tiempo específico"""
        # Usar configuración centralizada
        time_limit = ServiceConfig.get_time_limit(ServiceType.PACKAGING)
        tolerance_minutes = ServiceConfig.get_tolerance_minutes(ServiceType.PACKAGING)
        super().__init__(time_limit=time_limit, tolerance_minutes=tolerance_minutes)
        self.packaging_rule = PackagingRule()
    
    def filter_activities(self, activities_data: Dict[str, Any]) -> Dict[str, Any]:
        return self.packaging_rule.filter_activities(activities_data)
    
    def get_most_suitable_team(self, db: Session) -> Dict[str, Any]:
        return self.packaging_rule.get_most_suitable_team(db)
    
    def get_activity_for_order(self, order_data: Dict, activities_data: Dict) -> Optional[Dict]:
        return self.packaging_rule.get_activity_for_order(order_data, activities_data)
    
    def get_specific_team_for_activity(self, activity_name: str, activity_description: str, teams_data: Dict) -> Dict[str, Any]:
        return self.packaging_rule.get_specific_team_for_activity(
            activity_name, activity_description, teams_data
        )
    
    def get_packaging_activities_with_minutes(self, extracted_orders: List[Dict], db: Session) -> Dict[str, Any]:
        """
        Obtiene las actividades de empaque para todas las órdenes extraídas y calcula los minutos.
        
        Args:
            extracted_orders: Lista de órdenes extraídas (con lote, quantity, code)
            db: Sesión de base de datos
            
        Returns:
            Diccionario con actividades de empaque y minutos calculados
        """
        # Obtener todas las actividades
        all_activities = self.get_activities_for_orders(extracted_orders, db)
        
        # Filtrar solo las de empaque
        packaging_activities = self.filter_activities(all_activities)
        
        # Calcular minutos para cada actividad de empaque
        packaging_activities_with_minutes = {}
        packaging_activities_by_code = packaging_activities.get("packaging_activities_by_code", {})
        
        for code, code_data in packaging_activities_by_code.items():
            packaging_activities_list = code_data.get("packaging_activities", [])
            activities_with_minutes = []
            
            for activity_data in packaging_activities_list:
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
                            hours_calculation = performance * order_quantity
                            formula = f"{performance} horas * {order_quantity} = {hours_calculation} horas * 60 = {calculated_minutes} minutos (con ceiling)"
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
                packaging_activities_with_minutes[code] = {
                    "code": code,
                    "packaging_activities_with_minutes": activities_with_minutes,
                    "total_packaging_activities": len(activities_with_minutes),
                    "found": True
                }
        
        return {
            "all_activities": all_activities,
            "packaging_activities": packaging_activities,
            "packaging_activities_with_minutes": {
                "packaging_activities_with_minutes_by_code": packaging_activities_with_minutes,
                "total_codes_with_packaging_minutes": len(packaging_activities_with_minutes),
                "codes_with_packaging_minutes": list(packaging_activities_with_minutes.keys())
            },
            "total_orders_processed": len(extracted_orders)
        }
    
    def create_packaging_tasks_for_orders(self, extracted_orders: List[Dict], db: Session) -> Dict[str, Any]:
        """
        Función principal que maneja todo el proceso de creación de tareas de empaque.
        Utiliza la implementación base de create_tasks_for_orders pero con lógica específica
        para selección de equipos por actividad.
        
        Args:
            extracted_orders: Lista de órdenes extraídas con lote, quantity y code
            db: Sesión de base de datos
        
        Returns:
            Resultado del proceso con información de las tareas creadas
        """
        try:
            # Obtener actividades con minutos calculados
            activities_with_minutes = self.get_packaging_activities_with_minutes(extracted_orders, db)
            
            # Obtener todos los equipos de empaque disponibles
            teams_result = self.get_most_suitable_team(db)
            
            if not teams_result.get("success"):
                return {
                    "success": False,
                    "message": "No se pudo obtener equipos de empaque",
                    "tasks_created": 0,
                    "total_orders": len(extracted_orders)
                }
            
            # Procesar cada orden con selección específica de equipo
            created_tasks = []
            failed_orders = []
            
            packaging_activities_with_minutes = activities_with_minutes.get("packaging_activities_with_minutes", {}).get("packaging_activities_with_minutes_by_code", {})
            
            for order_data in extracted_orders:
                order_code = order_data.get('code')
                
                # Obtener la actividad con minutos calculados para esta orden
                code_activities = packaging_activities_with_minutes.get(order_code, {}).get("packaging_activities_with_minutes", [])
                
                if not code_activities:
                    failed_orders.append({
                        "order_data": order_data,
                        "reason": "No se encontró actividad válida"
                    })
                    continue
                
                # Usar la primera actividad de empaque
                activity_with_minutes = code_activities[0]
                activity_name = activity_with_minutes.get("activity_data", {}).get("activity", "")
                activity_description = activity_with_minutes.get("activity_data", {}).get("description", "")
                
                # Obtener el equipo específico para esta actividad
                team_selection = self.get_specific_team_for_activity(
                    activity_name, activity_description, teams_result
                )
                
                if not team_selection.get("success"):
                    failed_orders.append({
                        "order_data": order_data,
                        "reason": f"No se pudo asignar equipo para actividad: {activity_name}"
                    })
                    continue
                
                selected_team = team_selection.get("selected_team")
                team_id = selected_team.get("id")
                
                # Obtener programaciones disponibles para el equipo seleccionado
                available_programmings = self.get_available_programmings_for_team(team_id, db)
                
                if not available_programmings:
                    failed_orders.append({
                        "order_data": order_data,
                        "reason": f"No se encontraron programaciones para equipo: {selected_team.get('name')}"
                    })
                    continue
                
                # Calcular minutos de la tarea
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
                        "order_task": time_verification.get("order_task_created"),
                        "team_selection": team_selection
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
                "teams_data": teams_result,
                "activities_data": activities_with_minutes.get("packaging_activities")
            }
            
        except Exception as e:
            return {
                "success": False,
                "message": f"Error durante la creación de tareas de empaque: {str(e)}",
                "tasks_created": 0,
                "total_orders": len(extracted_orders)
            }
