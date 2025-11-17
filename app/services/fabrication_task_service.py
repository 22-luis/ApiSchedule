"""
Servicio refactorizado para manejar la creación de tareas de fabricación.
Hereda de BaseTaskService para reutilizar funcionalidad común.
"""

from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from datetime import date, time, datetime
import logging
import math

from app.services.base_task_service import BaseTaskService
from app.services.config import ServiceType, ServiceConfig
from app.utils.Auto.rules.Manufactured import ManufacturedRule


class FabricationTaskService(BaseTaskService):
    """Servicio para manejar la creación de tareas de fabricación"""
    
    def __init__(self):
        """Inicializa el servicio de fabricación con límite de tiempo específico"""
        # Usar configuración centralizada
        time_limit = ServiceConfig.get_time_limit(ServiceType.FABRICATION)
        tolerance_minutes = ServiceConfig.get_tolerance_minutes(ServiceType.FABRICATION)
        super().__init__(time_limit=time_limit, tolerance_minutes=tolerance_minutes)
        self.manufactured_rule = ManufacturedRule()
    
    def filter_activities(self, activities_data: Dict[str, Any]) -> Dict[str, Any]:
        return self.manufactured_rule.filter_activities(activities_data)
    
    def get_most_suitable_team(self, db: Session, order_data: Dict, activity_type: Optional[str] = None) -> Dict[str, Any]:
        return self.manufactured_rule.get_most_suitable_team(db, order_data, activity_type)
    
    def get_activity_for_order(self, order_data: Dict, activities_data: Dict) -> Optional[Dict]:
        return self.manufactured_rule.get_activity_for_order(order_data, activities_data)
    
    def get_specific_team_for_activity(self, order_data: Dict, teams_data: Dict) -> Dict[str, Any]:
        return self.manufactured_rule.get_specific_team_for_activity(
            order_data, teams_data
        )
    
    def get_fabrication_activities_with_minutes(self, extracted_orders: List[Dict], db: Session) -> Dict[str, Any]:
        """
        Obtiene las actividades de fabricación para todas las órdenes extraídas y calcula los minutos.
        
        Args:
            extracted_orders: Lista de órdenes extraídas (con lote, quantity, code)
            db: Sesión de base de datos
            
        Returns:
            Diccionario con actividades de fabricación y minutos calculados
        """
        # Obtener todas las actividades
        all_activities = self.get_activities_for_orders(extracted_orders, db)
        
        # Filtrar solo las de fabricación
        fabrication_activities = self.filter_activities(all_activities)
        
        # Calcular minutos para cada actividad de fabricación
        fabrication_activities_with_minutes = {}
        fabrication_activities_by_code = fabrication_activities.get("fabrication_activities_by_code", {})
        
        for code, code_data in fabrication_activities_by_code.items():
            fabrication_activities_list = code_data.get("fabrication_activities", [])
            activities_with_minutes = []
            
            for activity_data in fabrication_activities_list:
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
                fabrication_activities_with_minutes[code] = {
                    "code": code,
                    "fabrication_activities_with_minutes": activities_with_minutes,
                    "total_fabrication_activities": len(activities_with_minutes),
                    "found": True
                }
        
        return {
            "all_activities": all_activities,
            "fabrication_activities": fabrication_activities,
            "fabrication_activities_with_minutes": {
                "fabrication_activities_with_minutes_by_code": fabrication_activities_with_minutes,
                "total_codes_with_fabrication_minutes": len(fabrication_activities_with_minutes),
                "codes_with_fabrication_minutes": list(fabrication_activities_with_minutes.keys())
            },
            "total_orders_processed": len(extracted_orders)
        }
    
    def create_fabrication_tasks_for_orders(self, extracted_orders: List[Dict], db: Session, weighing_results: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Función principal que maneja todo el proceso de creación de tareas de fabricación.
        Utiliza la implementación base de create_tasks_for_orders pero con lógica específica
        para selección de equipos por actividad.
        
        Args:
            extracted_orders: Lista de órdenes extraídas con lote, quantity y code
            db: Sesión de base de datos
            weighing_results: Resultados de la creación de tareas de pesado (opcional)
        
        Returns:
            Resultado del proceso con información de las tareas creadas
        """
        try:
            # Crear un mapa de lote a fecha de finalización de pesado
            weighing_end_dates = {}
            if weighing_results and weighing_results.get("created_tasks"):
                for task in weighing_results["created_tasks"]:
                    lote = task.get("order_data", {}).get("lote")
                    end_time_str = task.get("order_task", {}).get("end_time")
                    if lote and end_time_str:
                        weighing_end_dates[lote] = datetime.fromisoformat(end_time_str).date()

            logger = logging.getLogger(__name__)

            # Obtener actividades con minutos calculados
            activities_with_minutes = self.get_fabrication_activities_with_minutes(extracted_orders, db)
            
            # Procesar cada orden con selección específica de equipo
            created_tasks = []
            failed_orders = []
            
            fabrication_activities_with_minutes = activities_with_minutes.get("fabrication_activities_with_minutes", {}).get("fabrication_activities_with_minutes_by_code", {})
            
            for order_data in extracted_orders:
                order_code = order_data.get('code')
                lote = order_data.get('lote')
                
                # Obtener la actividad con minutos calculados para esta orden
                code_activities = fabrication_activities_with_minutes.get(order_code, {}).get("fabrication_activities_with_minutes", [])
                
                if not code_activities:
                    failed_orders.append({
                        "order_data": order_data,
                        "reason": "No se encontró actividad válida"
                    })
                    continue
                
                # Usar la primera actividad de fabricación
                activity_with_minutes = code_activities[0]
                activity_name = activity_with_minutes.get("activity_data", {}).get("activity")

                # Obtener el equipo específico para esta actividad
                activity_details = activity_with_minutes.get("activity_data", {})
                activity_type = activity_details.get("type")
                team_selection = self.get_most_suitable_team(db, order_data, activity_type)
                
                if not team_selection.get("success"):
                    failed_orders.append({
                        "order_data": order_data,
                        "reason": f"No se pudo asignar equipo para actividad: {activity_name}"
                    })
                    continue
                
                selected_team = team_selection.get("selected_team")
                team_id = selected_team.get("id")
                
                # Determinar la fecha de inicio para la búsqueda de programación
                start_date_candidate = weighing_end_dates.get(lote)
                # Usar la fecha del pesado solo si es futura; en otro caso preferir hoy
                if start_date_candidate and isinstance(start_date_candidate, date) and start_date_candidate > date.today():
                    start_date = start_date_candidate
                else:
                    start_date = date.today()
                logger.debug(f"Fabrication: lote={lote} start_date_candidate={start_date_candidate} -> start_date_used={start_date}")

                # Obtener programaciones disponibles para el equipo seleccionado
                available_programmings = self.get_available_programmings_for_team(team_id, db, start_date=start_date)
                
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
                "activities_data": activities_with_minutes.get("fabrication_activities")
            }
            
        except Exception as e:
            # Log a more detailed error message, including traceback
            import traceback
            print(f"Error during fabrication task creation: {str(e)}\n{traceback.format_exc()}")
            
            # Rollback the transaction to avoid inconsistent state
            db.rollback()
            
            # Re-raise the exception so it's not silent
            raise