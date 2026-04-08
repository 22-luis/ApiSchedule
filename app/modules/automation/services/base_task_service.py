"""
Clase base abstracta para servicios de tareas.
Define la interfaz común que deben implementar todos los servicios de tareas.
"""

import math
from abc import ABC, abstractmethod
from datetime import time, timedelta, date, datetime
from typing import List, Dict, Any, Optional

from sqlalchemy.orm import Session

from app.modules.automation.rules.schedule import ScheduleRule
from app.modules.automation.services.utils.auto_create_programming import create_programming_if_not_exists
from app.shared.utils.core.time_utils import TimeZoneUtils
from app.shared.utils.core.logging import get_logger
from app.modules.automation.services.utils.programming_utils import ProgrammingUtils
from app.shared.utils.business.order_status_service import OrderStatusService
from app.shared.utils.business.programming_availability import restore_programmings_availability


class BaseTaskService(ABC):
    """Clase base abstracta para servicios de tareas"""
    
    def __init__(self, time_limit: time, tolerance_minutes: int = 5):
        self.time_limit = time_limit
        self.tolerance_minutes = tolerance_minutes
        self.max_allowed_minutes = time_limit.hour * 60 + time_limit.minute + tolerance_minutes
        self.schedule_rule = ScheduleRule(tolerance_minutes=tolerance_minutes, time_limit=time_limit)
    
    @abstractmethod
    def filter_activities(self, activities_data: Dict[str, Any]) -> Dict[str, Any]:
        pass
    
    @abstractmethod
    def get_most_suitable_team(self, db: Session) -> Dict[str, Any]:
        pass
    
    @abstractmethod
    def get_activity_for_order(self, order_data: Dict, activities_data: Dict) -> Optional[Dict]:
        pass

    @staticmethod
    def extract_order_data(orders: List) -> List[Dict[str, Any]]:
        return ProgrammingUtils.extract_order_data(orders)

    @staticmethod
    def get_activities_by_code(code: str, db: Session) -> Dict[str, Any]:
        return ProgrammingUtils.get_activities_by_code(code, db)

    @staticmethod
    def get_activities_for_orders(extracted_orders: List[Dict], db: Session) -> Dict[str, Any]:
        return ProgrammingUtils.get_activities_for_orders(extracted_orders, db)

    @staticmethod
    def get_activity_details_by_code_and_activity(code: str, activity: str, db: Session) -> Dict[str, Any]:
        return ProgrammingUtils.get_activity_details_by_code_and_activity(code, activity, db)

    @staticmethod
    def get_available_programmings_for_team(team_id: str, db: Session, start_date: Optional[date] = None) -> List[Dict[str, Any]]:
        return ProgrammingUtils.get_available_programmings_for_team(team_id, db, start_date=start_date)
    
    def get_service_config(self) -> Dict[str, Any]:
        from app.modules.automation.services.config import ServiceConfig
        service_type = self.__class__.__name__.replace('TaskService', '').upper()
        
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

    @staticmethod
    def calculate_minutes_from_performance_and_quantity(performance: float, quantity: int, time: float = None) -> int:
        if quantity is None:
            return 0
        
        if performance is not None:
                # Performance se interpreta como UNIDADES por HORA (throughput).
                # Tiempo por unidad (en horas) = 1 / performance.
                # Minutos totales = quantity * (1 / performance) * 60
                try:
                    if performance == 0:
                        return 0
                    minutes = quantity * (1.0 / performance) * 60
                    return math.ceil(minutes)
                except Exception:
                    return 0
        elif time is not None:
            # Usar, time directamente como minutos
            return math.ceil(time)
        else:
            return 30
    
    def create_preparation_task(self, programming_id: str, programming_tasks: List, db: Session) -> Dict[str, Any]:
        return self.schedule_rule.create_preparation_task(programming_id, programming_tasks, db)
    
    def verify_programming_time_limit(self, programmings: List[Dict], task_minutes: int, db: Session, 
                                    order_data: Optional[Dict] = None, 
                                    activity_details: Optional[Dict] = None) -> Dict[str, Any]:
        return self.schedule_rule.verify_programming_time_limit(programmings, task_minutes, db, order_data, activity_details)
    
    def create_tasks_for_orders(self, extracted_orders: List[Dict], db: Session) -> Dict[str, Any]:
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
            
            # Restaurar disponibilidad de programaciones (por si alguna válida estaba marcada como unavailable)
            restore_programmings_availability(db)

            # Obtener programaciones disponibles iniciando desde HOY
            available_programmings = self.get_available_programmings_for_team(team_id, db, start_date=date.today() + timedelta(days=1))
            
            # Filtrar explícitamente los domingos (weekday == 6)
            available_programmings = [
                p for p in available_programmings 
                if (p['date'] if isinstance(p['date'], date) else date.fromisoformat(p['date'])).weekday() != 6
            ]
            
            # Procesar cada orden (con lógica de agrupación para tareas <= 3 min)
            created_tasks = []
            failed_orders = []
            
            # Pre-procesar actividades y minutos para todas las órdenes
            orders_with_details = []
            for order_data in extracted_orders:
                activity = self.get_activity_for_order(order_data, filtered_activities)
                if not activity:
                    failed_orders.append({"order_data": order_data, "reason": "No se encontró actividad válida"})
                    continue
                
                if "activity_data" in activity:
                    activity_details = activity.get("activity_data", {})
                    task_minutes = activity.get("minutes_calculation", {}).get("calculated_minutes", 0)
                else:
                    activity_details = activity
                    task_minutes = self.calculate_minutes_from_performance_and_quantity(
                        activity.get("performance"), order_data.get("quantity"), activity.get("time")
                    )
                
                orders_with_details.append({
                    "order_data": order_data,
                    "activity_details": activity_details,
                    "task_minutes": task_minutes
                })

            # Agrupar órdenes consecutivas que cumplen el criterio (mismo código y <= 3 min)
            task_groups = []
            current_group = []
            
            for item in orders_with_details:
                code = item['order_data'].get('code')
                mins = item['task_minutes']
                
                if (current_group and 
                    code == current_group[0]['order_data'].get('code') and 
                    mins <= 3 and 
                    current_group[0]['task_minutes'] <= 3):
                    current_group.append(item)
                else:
                    if current_group:
                        task_groups.append(current_group)
                    current_group = [item]
            if current_group:
                task_groups.append(current_group)

            # Procesar grupos de tareas
            for group in task_groups:
                # --- CHECK FOR DUPLICATES START ---
                from app.modules.programming.models.task import Task
                from app.modules.programming.models.programming import ProgrammingTask
                
                valid_group_items = []
                for item in group:
                    order_data = item['order_data']
                    activity_details = item['activity_details']
                    target_lote = order_data.get("lote")
                    activity_type = activity_details.get("type")
                    activity_name = activity_details.get("activity")
                    
                    if target_lote and (activity_type or activity_name):
                        existing_task = db.query(Task).filter(Task.lote == str(target_lote)).filter(
                            (Task.type == activity_type) if activity_type else (Task.activity == activity_name)
                        ).first()
                        
                        if existing_task:
                            pt = db.query(ProgrammingTask).filter(ProgrammingTask.task_id == existing_task.id).first()
                            logger.info(f"Existing task found for order {target_lote} type {activity_type or activity_name}. SKIPPING.")
                            try:
                                OrderStatusService.update_order_status_for_task_creation(db, existing_task)
                            except Exception as e:
                                logger.error(f"Error updating order status for existing task: {e}")
                            
                            prog_date = None
                            team_name = None
                            if pt:
                                from app.modules.programming.models.programming import Programming
                                from app.modules.organization.models.team import Team
                                prog = db.query(Programming).filter(Programming.id == pt.programming_id).first()
                                if prog:
                                    prog_date = str(prog.date)
                                    tm = db.query(Team).filter(Team.id == prog.team_id).first()
                                    if tm: team_name = tm.name

                            created_tasks.append({
                                "order_data": order_data,
                                "selected_programming": {"id": str(pt.programming_id) if pt else None, "date": prog_date, "team_name": team_name},
                                "order_task": {"task_id": str(existing_task.id), "programming_id": str(pt.programming_id) if pt else None, "status": "existing"}
                            })
                            continue
                    
                    valid_group_items.append(item)
                
                if not valid_group_items:
                    continue
                
                # Re-evaluar el grupo con los elementos válidos (no duplicados)
                group = valid_group_items
                # --- CHECK FOR DUPLICATES END ---

                # Si el grupo tiene más de un elemento, promediar tiempo y cantidad
                if len(group) > 1:
                    total_mins = sum(item['task_minutes'] for item in group)
                    total_qty = sum(item['order_data'].get('quantity', 0) for item in group)
                    avg_mins = total_mins / len(group)
                    avg_qty = total_qty / len(group)
                    
                    for item in group:
                        item['task_minutes'] = avg_mins
                        item['order_data']['quantity'] = avg_qty
                    
                    # El tiempo total a programar es la suma de los minutos promediados (o sea, el total original)
                    minutes_to_schedule = total_mins
                else:
                    minutes_to_schedule = group[0]['task_minutes']

                if minutes_to_schedule <= 0:
                    for item in group:
                        failed_orders.append({"order_data": item['order_data'], "reason": "Los minutos calculados no son válidos"})
                    continue

                # Intentar programar el grupo
                current_prog_idx = 0
                group_scheduled = False
                attempts = 0
                max_attempts = 100
                
                # Variables para compartir tiempo entre miembros del grupo
                group_start_time = None
                group_end_time = None
                
                while not group_scheduled and attempts < max_attempts:
                    attempts += 1
                    
                    if current_prog_idx >= len(available_programmings):
                        # Lógica de creación de nueva programación
                        last_date = available_programmings[-1]['date'] if available_programmings else date.today() + timedelta(days=1)
                        if isinstance(last_date, str): last_date = date.fromisoformat(last_date)
                        next_date = last_date + timedelta(days=1)
                        if next_date.weekday() == 6: next_date += timedelta(days=1)
                        
                        new_prog_result = create_programming_if_not_exists(db, team_id, next_date)
                        if new_prog_result['success']:
                            p = new_prog_result['programming']
                            available_programmings.append({"id": str(p.id), "date": p.date, "status": p.status, "team_id": str(p.team_id)})
                        else:
                            for item in group: failed_orders.append({"order_data": item['order_data'], "reason": f"No se pudo crear nueva programación: {new_prog_result.get('message')}"})
                            break
                    
                    current_prog = available_programmings[current_prog_idx]
                    
                    # Primero verificar disponibilidad para el tiempo TOTAL del grupo
                    time_verification = self.verify_programming_time_limit([current_prog], minutes_to_schedule, db)
                    
                    if time_verification.get("success"):
                        # Si hay tiempo, crear cada tarea del grupo compartiendo el horario
                        selected_prog_data = time_verification.get("selected_programming")
                        
                        # El primer elemento define el horario para todos
                        first_item = group[0]
                        first_task_verification = self.verify_programming_time_limit(
                            [current_prog], minutes_to_schedule, db, first_item['order_data'], first_item['activity_details'],
                            metadata_minutes=int(first_item['task_minutes'])
                        )
                        
                        if first_task_verification.get("success") and first_task_verification.get("order_task_created"):
                            task_data = first_task_verification.get("order_task_created")
                            group_start_time = datetime.fromisoformat(task_data['start_time'])
                            group_end_time = datetime.fromisoformat(task_data['end_time'])
                            
                            created_tasks.append({
                                "order_data": first_item['order_data'],
                                "selected_programming": selected_prog_data,
                                "order_task": task_data
                            })
                            
                            # Crear el resto de las tareas con el MISMO tiempo (override) y task_minutes = 0 para no sumar más
                            for i in range(1, len(group)):
                                item = group[i]
                                item_verification = self.verify_programming_time_limit(
                                    [current_prog], 0, db, item['order_data'], item['activity_details'],
                                    override_start_time=group_start_time,
                                    override_end_time=group_end_time,
                                    metadata_minutes=int(item['task_minutes'])
                                )
                                if item_verification.get("success") and item_verification.get("order_task_created"):
                                    created_tasks.append({
                                        "order_data": item['order_data'],
                                        "selected_programming": selected_prog_data,
                                        "order_task": item_verification.get("order_task_created")
                                    })
                            
                            group_scheduled = True
                        else:
                            current_prog_idx += 1
                    else:
                        current_prog_idx += 1

                if not group_scheduled and attempts >= max_attempts:
                    for item in group:
                        failed_orders.append({"order_data": item['order_data'], "reason": "No se pudo programar el grupo después de múltiples intentos"})

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
            import traceback
            traceback.print_exc()
            return {
                "success": False,
                "message": f"Error durante la creación de tareas: {str(e)}",
                "tasks_created": 0,
                "total_orders": len(extracted_orders)
            }
