"""
Servicio refactorizado para manejar la creación de tareas de pesado.
Hereda de BaseTaskService para reutilizar funcionalidad común.
"""

from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from datetime import time
import math
import logging

logger = logging.getLogger(__name__)

from app.modules.automation.services.base_task_service import BaseTaskService
from app.modules.automation.services.config import ServiceType, ServiceConfig
from app.modules.automation.rules.weighning import WeighingRule


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
            
            # Procesar cada orden
            created_tasks = []
            failed_orders = []
            
            weighing_activities_with_minutes = activities_with_minutes.get("weighing_activities_with_minutes", {}).get("weighing_activities_with_minutes_by_code", {})
            
            for order_data in extracted_orders:
                order_code = order_data.get('code')
                lote = order_data.get('lote')
                
                # CORREGIDO: Usar actividades por LOTE específico, no por código
                code_data = weighing_activities_with_minutes.get(order_code, {})
                activities_by_lote = code_data.get("weighing_activities_by_lote", {})
                lote_activities = activities_by_lote.get(lote, [])
                
                if not lote_activities:
                    failed_orders.append({
                        "order_data": order_data,
                        "reason": "No se encontró actividad válida"
                    })
                    continue
                
                # Usar la primera actividad de pesado para este lote
                activity_with_minutes = lote_activities[0]
                task_minutes = activity_with_minutes.get("minutes_calculation", {}).get("calculated_minutes", 0)
                activity_details = activity_with_minutes.get("activity_data", {})
                activity_type = activity_details.get("type")

                # --- DUPLICATE CHECK START ---
                from app.modules.programming.models.task import Task
                from app.modules.programming.models.order import Order
                from app.modules.programming.models.state import OrderStatus
                from app.modules.programming.models.programming import ProgrammingTask
                
                target_lote = order_data.get("lote")
                
                if target_lote and activity_type:
                    existing_task = db.query(Task).filter(
                        Task.lote == str(target_lote),
                        Task.type == activity_type
                    ).first()
                    
                    if existing_task:
                         # Treat as success to preserve existing data
                         pt = db.query(ProgrammingTask).filter(ProgrammingTask.task_id == existing_task.id).first()
                         
                         # Log retrieval of existing task
                         logger.info(f"Existing task found for order {target_lote} type {activity_type}. SKIPPING CREATION.")
                         
                         # Update order status to 'programmed' even if task already exists
                         try:
                             from app.modules.programming.services.order_status_service import OrderStatusService
                             OrderStatusService.update_order_status_for_task_creation(db, existing_task)
                             logger.info(f"Updated order status for existing task lote={target_lote}")
                         except Exception as e:
                             logger.error(f"Error updating order status for existing task: {e}")

                         # Get team name for the notification
                         team_name = None
                         programming_date = None
                         if pt:
                             from app.modules.programming.models.programming import Programming
                             from app.modules.core.models.team import Team
                             
                             prog = db.query(Programming).filter(Programming.id == pt.programming_id).first()
                             if prog:
                                 programming_date = str(prog.date)
                                 tm = db.query(Team).filter(Team.id == prog.team_id).first()
                                 if tm:
                                     team_name = tm.name

                         created_tasks.append({
                            "order_data": order_data,
                            "selected_programming": {
                                "id": str(pt.programming_id) if pt else None,
                                "date": programming_date or (str(pt.start_time.date()) if pt and pt.start_time else None),
                                "team_name": team_name
                            },
                            "order_task": {
                                "task_id": str(existing_task.id),
                                "programming_id": str(pt.programming_id) if pt else None,
                                "status": "existing"
                            }
                         })
                         continue
                # --- DUPLICATE CHECK END ---
                
                if task_minutes <= 0:
                    failed_orders.append({
                        "order_data": order_data,
                        "reason": "Los minutos calculados no son válidos"
                    })
                    continue

                # OBTENER EQUIPO IDÓNEO POR ORDEN
                team_result = self.get_most_suitable_team(db, order_data=order_data, activity_type=activity_type)
                
                if not team_result.get("success"):
                     failed_orders.append({
                        "order_data": order_data,
                        "reason": team_result.get("reason", "No se pudo obtener equipo idóneo para esta orden")
                    })
                     continue

                team_id = team_result.get("most_suitable_team", {}).get("id")
                
                # Obtener programaciones disponibles para este equipo
                # Nota: Podríamos optimizar cacheando si es el mismo equipo, pero para seguridad y corrección lo traemos fresco
                available_programmings = self.get_available_programmings_for_team(team_id, db)
                
                if not available_programmings:
                     failed_orders.append({
                        "order_data": order_data,
                        "reason": "No se encontraron programaciones disponibles para el equipo seleccionado"
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
