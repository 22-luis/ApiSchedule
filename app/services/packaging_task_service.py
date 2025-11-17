"""
Servicio refactorizado para manejar la creación de tareas de empaque.
Hereda de BaseTaskService para reutilizar funcionalidad común.
"""

from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from datetime import date, time, datetime
import logging
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

    def get_packaging_teams(self, db: Session) -> Dict[str, Any]:
        """
        Obtiene todos los equipos de empaque.
        Este método es un placeholder y debería ser implementado en PackagingRule
        o una clase de utilidad de equipos si la lógica es compleja.
        """
        return self.packaging_rule.get_packaging_teams(db)

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
    
    def create_packaging_tasks_for_orders(self, extracted_orders: List[Dict], db: Session, fabrication_results: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Función principal que maneja todo el proceso de creación de tareas de empaque.
        """
        try:
            logger = logging.getLogger(__name__)

            fabrication_end_dates = {}
            if fabrication_results and fabrication_results.get("created_tasks"):
                for task in fabrication_results["created_tasks"]:
                    lote = task.get("order_data", {}).get("lote")
                    end_time_str = task.get("order_task", {}).get("end_time")
                    if lote and end_time_str:
                        fabrication_end_dates[lote] = datetime.fromisoformat(end_time_str).date()

            activities_data = self.get_packaging_activities_with_minutes(extracted_orders, db)
            packaging_activities_by_code = activities_data.get("packaging_activities_with_minutes", {}).get("packaging_activities_with_minutes_by_code", {})

            teams_data = self.get_packaging_teams(db)
            if not teams_data.get("success"):
                return {"success": False, "message": "No se encontraron equipos de empaque.", "tasks_created": 0}

            created_tasks = []
            failed_orders = []

            for order_data in extracted_orders:
                code = order_data.get("code")
                lote = order_data.get("lote")
                activities_for_code = packaging_activities_by_code.get(code, {}).get("packaging_activities_with_minutes", [])

                if not activities_for_code:
                    failed_orders.append({"order_data": order_data, "reason": "No se encontraron actividades de empaque para el código."})
                    continue

                for activity in activities_for_code:
                    activity_details = activity.get("activity_data", {})
                    task_minutes = activity.get("minutes_calculation", {}).get("calculated_minutes", 0)

                    if task_minutes <= 0:
                        failed_orders.append({"order_data": order_data, "reason": "Minutos calculados no válidos."})
                        continue

                    team_selection = self.get_specific_team_for_activity(
                        activity_details.get("activity"),
                        activity_details.get("description"),
                        teams_data
                    )

                    if not team_selection.get("success"):
                        # TeamSelectionService returns 'reason' (and sometimes 'message'), use either
                        failed_orders.append({"order_data": order_data, "reason": team_selection.get("reason") or team_selection.get("message")})
                        continue

                    # TeamSelectionService returns the chosen team under the key 'selected_team'
                    selected_team = team_selection.get("selected_team") or team_selection.get("team") or {}
                    team_id = selected_team.get("id")
                    start_date_candidate = fabrication_end_dates.get(lote)
                    if start_date_candidate and isinstance(start_date_candidate, date) and start_date_candidate > date.today():
                        start_date = start_date_candidate
                    else:
                        start_date = date.today()
                    logger.debug(f"Packaging: lote={lote} start_date_candidate={start_date_candidate} -> start_date_used={start_date}")

                    available_programmings = self.get_available_programmings_for_team(team_id, db, start_date=start_date)

                    if not available_programmings:
                        failed_orders.append({"order_data": order_data, "reason": f"No hay programaciones disponibles para el equipo {team_id}."})
                        continue

                    time_verification = self.verify_programming_time_limit(
                        available_programmings, task_minutes, db, order_data, activity_details
                    )

                    if time_verification.get("success"):
                        created_tasks.append({
                            "order_data": order_data,
                            "selected_programming": time_verification.get("selected_programming"),
                            "order_task": time_verification.get("order_task_created")
                        })
                    else:
                        failed_orders.append({"order_data": order_data, "reason": time_verification.get("message")})

            return {
                "success": True,
                "message": f"Procesamiento de empaque completado. {len(created_tasks)} tareas creadas.",
                "tasks_created": len(created_tasks),
                "total_orders": len(extracted_orders),
                "created_tasks": created_tasks,
                "failed_orders": failed_orders
            }

        except Exception as e:
            return {
                "success": False,
                "message": f"Error durante la creación de tareas de empaque: {str(e)}",
                "tasks_created": 0,
                "total_orders": len(extracted_orders)
            }
