"""
Servicio refactorizado para manejar la creación de tareas de pesado.
Hereda de BaseTaskService para reutilizar funcionalidad común.
"""

from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from datetime import time, date, timedelta
import math
import logging

logger = logging.getLogger(__name__)

from app.modules.automation.services.base_task_service import BaseTaskService
from app.modules.automation.services.config import ServiceType, ServiceConfig
from app.modules.automation.rules.weighning import WeighingRule
from app.shared.utils.business.programming_availability import restore_programmings_availability


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
    
    def get_most_suitable_team(self, db: Session, order_data: Dict = None, activity_type: Optional[str] = None) -> Dict[str, Any]:
        return self.weighing_rule.get_most_suitable_team(db, order_data=order_data, activity_type=activity_type)
    
    def get_activity_for_order(self, order_data: Dict, activities_data: Dict) -> Optional[Dict]:
        return self.weighing_rule.get_activity_for_order(order_data, activities_data)
    
    def get_weighing_activities_with_minutes(self, extracted_orders: List[Dict], db: Session) -> Dict[str, Any]:
        """
        Obtiene las actividades de pesado para todas las órdenes extraídas y calcula los minutos.
        CORREGIDO: Ahora calcula minutos POR ORDEN (lote) en lugar de por código.
        
        Args:
            extracted_orders: Lista de órdenes extraídas (con lote, quantity, code)
            db: Sesión de base de datos
            
        Returns:
            Diccionario con actividades de pesado y minutos calculados por lote
        """
        # Obtener todas las actividades
        all_activities = self.get_activities_for_orders(extracted_orders, db)
        
        # Filtrar solo las de pesado
        weighing_activities = self.filter_activities(all_activities)
        weighing_activities_by_code = weighing_activities.get("weighing_activities_by_code", {})
        
        # NUEVO: Calcular minutos POR CADA ORDEN (lote), no por código
        weighing_activities_with_minutes_by_code = {}
        
        for order in extracted_orders:
            code = order.get("code")
            lote = order.get("lote")
            order_quantity = order.get("quantity")
            
            if not code or order_quantity is None:
                continue
            
            code_data = weighing_activities_by_code.get(code, {})
            weighing_activities_list = code_data.get("weighing_activities", [])
            
            activities_with_minutes = []
            
            for activity_data in weighing_activities_list:
                activity_name = activity_data.get("activity")
                if activity_name:
                    # Calcular minutos usando la cantidad de ESTA orden específica
                    performance = activity_data.get("performance")
                    time_val = activity_data.get("time")
                    calculated_minutes = self.calculate_minutes_from_performance_and_quantity(
                        performance, order_quantity, time_val
                    )
                    
                    # Calcular horas para mostrar en la fórmula
                    if performance:
                        try:
                            hours_calc = order_quantity * (1.0 / performance) if performance != 0 else 0
                            hours_calculation = hours_calc
                            formula = f"{order_quantity} / {performance} = {hours_calculation:.4f} horas * 60 = {calculated_minutes} minutos (con ceiling)"
                        except Exception:
                            hours_calculation = 0
                            formula = f"Error calculando fórmula: performance={performance}, quantity={order_quantity}"
                    elif time_val:
                        hours_calculation = 0
                        formula = f"Tiempo directo: {time_val} minutos = {calculated_minutes} minutos (con ceiling)"
                    else:
                        hours_calculation = 0
                        formula = f"Valor por defecto: {calculated_minutes} minutos"
                    
                    activities_with_minutes.append({
                        "activity_data": activity_data,
                        "minutes_calculation": {
                            "performance": performance,
                            "time": time_val,
                            "quantity": order_quantity,
                            "lote": lote,
                            "hours_calculation": hours_calculation,
                            "calculated_minutes": calculated_minutes,
                            "formula": formula
                        }
                    })
            
            if activities_with_minutes:
                # Almacenar por código Y lote para poder buscar por ambos
                if code not in weighing_activities_with_minutes_by_code:
                    weighing_activities_with_minutes_by_code[code] = {
                        "code": code,
                        "weighing_activities_with_minutes": [],
                        "weighing_activities_by_lote": {},
                        "total_weighing_activities": 0,
                        "found": True
                    }
                
                # Agregar actividades para este lote específico
                weighing_activities_with_minutes_by_code[code]["weighing_activities_by_lote"][lote] = activities_with_minutes
                weighing_activities_with_minutes_by_code[code]["weighing_activities_with_minutes"].extend(activities_with_minutes)
                weighing_activities_with_minutes_by_code[code]["total_weighing_activities"] = len(
                    weighing_activities_with_minutes_by_code[code]["weighing_activities_with_minutes"]
                )
        
        return {
            "all_activities": all_activities,
            "weighing_activities": weighing_activities,
            "weighing_activities_with_minutes": {
                "weighing_activities_with_minutes_by_code": weighing_activities_with_minutes_by_code,
                "total_codes_with_weighing_minutes": len(weighing_activities_with_minutes_by_code),
                "codes_with_weighing_minutes": list(weighing_activities_with_minutes_by_code.keys())
            },
            "total_orders_processed": len(extracted_orders)
        }
    
    def create_weighing_tasks_for_orders(self, extracted_orders: List[Dict], db: Session) -> Dict[str, Any]:
        """
        Función principal que maneja todo el proceso de creación de tareas de pesado.
        Utiliza la implementación base de create_tasks_for_orders.
        
        Args:
            extracted_orders: Lista de órdenes extraídas con lote, quantity y code
            db: Sesión de base de datos
        
        Returns:
            Resultado del proceso con información de las tareas creadas
        """
        # Simplemente llamamos a la implementación base consolidada
        return self.create_tasks_for_orders(extracted_orders, db)
