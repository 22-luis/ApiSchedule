"""
Servicio refactorizado para manejar la creación de tareas de empaque.
Hereda de BaseTaskService para reutilizar funcionalidad común.
"""

from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from datetime import date, time, datetime
import logging
import math

logger = logging.getLogger(__name__)

from app.modules.automation.services.base_task_service import BaseTaskService
from app.modules.automation.services.config import ServiceType, ServiceConfig
from app.modules.automation.rules.packaging import PackagingRule


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
        CORREGIDO: Ahora calcula minutos POR ORDEN (lote) en lugar de por código.
        
        Args:
            extracted_orders: Lista de órdenes extraídas (con lote, quantity, code)
            db: Sesión de base de datos
            
        Returns:
            Diccionario con actividades de empaque y minutos calculados por lote
        """
        # Obtener todas las actividades
        all_activities = self.get_activities_for_orders(extracted_orders, db)
        
        # Filtrar solo las de empaque
        packaging_activities = self.filter_activities(all_activities)
        packaging_activities_by_code = packaging_activities.get("packaging_activities_by_code", {})
        
        # NUEVO: Calcular minutos POR CADA ORDEN (lote), no por código
        packaging_activities_with_minutes_by_code = {}
        
        for order in extracted_orders:
            code = order.get("code")
            lote = order.get("lote")
            order_quantity = order.get("quantity")
            
            if not code or order_quantity is None:
                continue
            
            code_data = packaging_activities_by_code.get(code, {})
            packaging_activities_list = code_data.get("packaging_activities", [])
            
            activities_with_minutes = []
            
            for activity_data in packaging_activities_list:
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
                if code not in packaging_activities_with_minutes_by_code:
                    packaging_activities_with_minutes_by_code[code] = {
                        "code": code,
                        "packaging_activities_with_minutes": [],
                        "packaging_activities_by_lote": {},
                        "total_packaging_activities": 0,
                        "found": True
                    }
                
                # Agregar actividades para este lote específico
                packaging_activities_with_minutes_by_code[code]["packaging_activities_by_lote"][lote] = activities_with_minutes
                packaging_activities_with_minutes_by_code[code]["packaging_activities_with_minutes"].extend(activities_with_minutes)
                packaging_activities_with_minutes_by_code[code]["total_packaging_activities"] = len(
                    packaging_activities_with_minutes_by_code[code]["packaging_activities_with_minutes"]
                )
        
        return {
            "all_activities": all_activities,
            "packaging_activities": packaging_activities,
            "packaging_activities_with_minutes": {
                "packaging_activities_with_minutes_by_code": packaging_activities_with_minutes_by_code,
                "total_codes_with_packaging_minutes": len(packaging_activities_with_minutes_by_code),
                "codes_with_packaging_minutes": list(packaging_activities_with_minutes_by_code.keys())
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
                
                # CORREGIDO: Usar actividades por LOTE específico, no por código
                code_data = packaging_activities_by_code.get(code, {})
                activities_by_lote = code_data.get("packaging_activities_by_lote", {})
                activities_for_order = activities_by_lote.get(lote, [])

                if not activities_for_order:
                    failed_orders.append({"order_data": order_data, "reason": "No se encontraron actividades de empaque para el código."})
                    continue

                # CORREGIDO: Usar get_activity_for_order para seleccionar UNA SOLA actividad según las reglas de prioridad
                # En lugar de iterar sobre todas las actividades
                selected_activity = self.get_activity_for_order(order_data, {
                    "packaging_activities_by_code": {
                        code: {
                            "packaging_activities": [a.get("activity_data", {}) for a in activities_for_order]
                        }
                    }
                })
                
                if not selected_activity:
                    failed_orders.append({"order_data": order_data, "reason": "No se pudo seleccionar actividad de empaque."})
                    continue
                
                # Buscar los minutos calculados para esta actividad específica
                activity_name = selected_activity.get("activity", "")
                activity_type = selected_activity.get("type", "")

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
                task_minutes = 0
                activity_details = selected_activity
                
                for activity in activities_for_order:
                    act_data = activity.get("activity_data", {})
                    if act_data.get("activity") == activity_name or act_data.get("type") == activity_type:
                        task_minutes = activity.get("minutes_calculation", {}).get("calculated_minutes", 0)
                        activity_details = act_data
                        break

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
