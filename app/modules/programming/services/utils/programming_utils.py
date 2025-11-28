from typing import List, Dict, Any, Optional
import uuid
from sqlalchemy.orm import Session
from datetime import datetime, time, timedelta, date

from app.modules.programming.models.order import Order
from app.modules.codes.models.code import Code
# from app.modules.codes.models.preparation import Preparation
from app.modules.programming.models.programming import Programming, ProgrammingTask
from app.modules.programming.models.state import ProgrammingStatus
from app.modules.programming.models.task import Task
from app.modules.core.models.team import Team
from app.shared.utils.business.programming_availability import check_programming_availability

class ProgrammingUtils:
    @staticmethod
    def extract_order_data(orders: List[Order]) -> List[Dict[str, Any]]:
        """
        Extrae datos básicos de una lista de órdenes.
        """
        # Debug logging to file
        try:
            with open("debug_extract.log", "a") as f:
                f.write(f"[{datetime.now()}] extract_order_data called with {len(orders) if orders else 0} orders\n")
                if orders:
                    for i, o in enumerate(orders):
                        f.write(f"  Order {i}: Lote={o.lote}, Code={o.code}, Qty={o.quantity}, Bin={o.bin}\n")
                else:
                    f.write("  Orders list is empty or None\n")
        except Exception as e:
            pass

        extracted_data = []
        if orders:
            for order in orders:
                extracted_data.append({
                    "lote": order.lote,
                    "quantity": order.quantity,
                    "code": order.code,
                    "order_id": order.lote,
                    "description": order.description
                })
        
        try:
            with open("debug_extract.log", "a") as f:
                f.write(f"[{datetime.now()}] extracted_data result: {len(extracted_data)} items\n")
        except:
            pass
            
        return extracted_data

    @staticmethod
    def get_activities_by_code(code: str, db: Session) -> Dict[str, Any]:
        """
        Obtiene las actividades (preparaciones) asociadas a un código.
        """
        code_objs = db.query(Code).filter(Code.code == code).all()
        if not code_objs:
            return {"success": False, "message": f"Code {code} not found"}
        
        activities = []
        # Usamos la información del código directamente ya que Preparation no tiene la info necesaria
        for code_obj in code_objs:
            if code_obj.activity:
                activities.append({
                    "activity": code_obj.activity,
                    "performance": code_obj.performance,
                    "time": code_obj.time,
                    "preparation_id": code_obj.id, # Usamos el ID del código como referencia
                    "code_id": code_obj.id,
                    "people": code_obj.people,
                    "material": code_obj.material,
                    "presentation": code_obj.presentation,
                    "fabricationCode": code_obj.fabricationCode,
                    "usefulLife": code_obj.usefulLife,
                    "unit": code_obj.unit,
                    "type": code_obj.type,
                    "description": code_obj.description
                })
            
        return {
            "success": True,
            "code": code,
            "activities": activities
        }

    @staticmethod
    def get_activities_for_orders(extracted_orders: List[Dict], db: Session) -> Dict[str, Any]:
        """
        Obtiene actividades para una lista de órdenes extraídas.
        Agrupa por código para evitar consultas repetidas.
        """
        unique_codes = set(order['code'] for order in extracted_orders if order.get('code'))
        activities_by_code = {}
        
        for code in unique_codes:
            result = ProgrammingUtils.get_activities_by_code(code, db)
            if result.get("success"):
                # Adaptar estructura para que coincida con lo esperado por los servicios
                # Los servicios esperan algo como "weighing_activities" o "fabrication_activities"
                # Aquí devolvemos una lista genérica y dejamos que el servicio filtre
                activities_by_code[code] = {
                    "weighing_activities": result.get("activities", []),
                    "fabrication_activities": result.get("activities", []),
                    "packaging_activities": result.get("activities", []),
                    "activities": result.get("activities", [])
                }
                
        return {
            "activities_by_code": activities_by_code,
            # Alias para compatibilidad con diferentes servicios
            "weighing_activities_by_code": activities_by_code,
            "fabrication_activities_by_code": activities_by_code,
            "packaging_activities_by_code": activities_by_code
        }

    @staticmethod
    def get_activity_details_by_code_and_activity(code: str, activity_name: str, db: Session) -> Dict[str, Any]:
        """
        Obtiene detalles de una actividad específica para un código.
        """
        code_obj = db.query(Code).filter(Code.code == code).first()
        if not code_obj:
            return {"success": False, "message": f"Code {code} not found"}
            
        # For now, using Code model directly as Preparation is commented out
        if code_obj.activity == activity_name:
            return {
                "success": True,
                "activity_details": {
                    "activity": code_obj.activity,
                    "performance": code_obj.performance,
                    "time": code_obj.time,
                    "preparation_id": code_obj.id, # Using code_obj.id as reference
                    "code_id": code_obj.id, # Added code_id for Task creation
                    "people": code_obj.people,
                    "material": code_obj.material,
                    "presentation": code_obj.presentation,
                    "fabricationCode": code_obj.fabricationCode,
                    "usefulLife": code_obj.usefulLife,
                    "unit": code_obj.unit,
                    "type": code_obj.type
                }
            }
        else:
            return {"success": False, "message": f"Activity {activity_name} not found for code {code}"}

    @staticmethod
    def get_available_programmings_for_team(team_id: str, db: Session, start_date: Optional[date] = None) -> List[Dict[str, Any]]:
        """
        Obtiene programaciones disponibles para un equipo.
        """
        query = db.query(Programming).filter(
            Programming.team_id == team_id,
            Programming.status == ProgrammingStatus.available
        )
        
        if start_date:
            query = query.filter(Programming.date >= start_date)
            
        programmings = query.order_by(Programming.date).all()
        
        result = []
        for prog in programmings:
            # Se ha deshabilitado el chequeo estricto aquí (check_programming_availability) para permitir 
            # que verify_programming_time_limit tome la decisión final basada en la capacidad real.
            result.append({
                "id": prog.id,
                "date": prog.date,
                "status": prog.status,
                "team_id": prog.team_id
            })
                
        return result

    @staticmethod
    def calculate_current_programming_time(programming_tasks: List[ProgrammingTask], programming_date: date) -> int:
        """
        Calcula el tiempo ocupado (en minutos desde el inicio del día) basado en las tareas.
        """
        if not programming_tasks:
            # Si no hay tareas, asumimos inicio a las 7:00 AM (420 minutos)
            return 420 
            
        # Encontrar la tarea que termina más tarde
        last_end_time = None
        for task in programming_tasks:
            if task.end_time:
                # Si end_time es datetime, extraer time. Si es time, usarlo.
                # Asumimos que end_time es datetime en la base de datos
                if isinstance(task.end_time, datetime):
                    et = task.end_time.time()
                else:
                    et = task.end_time
                
                if last_end_time is None or et > last_end_time:
                    last_end_time = et
                    
        if last_end_time:
            return last_end_time.hour * 60 + last_end_time.minute
        
        return 420 # Default start time if logic fails

    @staticmethod
    def create_order_task(programming_id: str, programming_tasks: List[ProgrammingTask], task_minutes: int, 
                         order_data: Dict, activity_details: Dict, db: Session) -> Dict[str, Any]:
        """
        Crea una tarea de programación para una orden.
        """
        try:
            # Calcular hora de inicio basada en tareas existentes
            start_minutes = ProgrammingUtils.calculate_current_programming_time(programming_tasks, date.today())
            
            # Convertir minutos a hora
            start_hour = start_minutes // 60
            start_minute = start_minutes % 60
            start_time_obj = time(start_hour, start_minute)
            
            # Calcular hora de fin
            end_minutes = start_minutes + task_minutes
            end_hour = end_minutes // 60
            end_minute = end_minutes % 60
            end_time_obj = time(end_hour, end_minute)
            
            # Crear objetos datetime combinando la fecha actual con la hora calculada
            today = date.today()
            start_datetime = datetime.combine(today, start_time_obj)
            end_datetime = datetime.combine(today, end_time_obj)
            
            task_id = uuid.uuid4()
            next_order = order_data.get("lote")

            # Crear la tarea principal
            new_task = Task(
                id=task_id,
                code_id=activity_details.get("code_id"),
                lote=str(order_data.get("lote")),
                quantity=order_data.get("quantity"),
                minutes=task_minutes,
                description=order_data.get("description"),
                status='pendiente',
                # Campos adicionales de activity_details
                activity=activity_details.get("activity"),
                people=activity_details.get("people"),
                performance=activity_details.get("performance"),
                # time=activity_details.get("time"), # Removed invalid argument
                material=activity_details.get("material"),
                presentation=activity_details.get("presentation"),
                fabricationCode=activity_details.get("fabricationCode"),
                usefulLife=activity_details.get("usefulLife"),
                unit=activity_details.get("unit"),
                type=activity_details.get("type")
            )
            db.add(new_task)
            db.flush() # Para asegurar que el ID esté disponible si fuera autogenerado (aunque aquí usamos uuid)

            # Crear la relación ProgrammingTask
            new_programming_task = ProgrammingTask(
                programming_id=programming_id,
                task_id=new_task.id,
                order=next_order,
                start_time=start_datetime,
                end_time=end_datetime,
                duration_in_hours=task_minutes / 60.0
            )
            
            db.add(new_programming_task)
            db.commit()
            
            return {
                "success": True,
                "message": "Task created successfully",
                "task_data": {
                    "task_id": str(new_task.id),
                    "programming_id": str(programming_id),
                    "start_time": start_datetime.isoformat(),
                    "end_time": end_datetime.isoformat(),
                    "order": next_order
                }
            }
            
        except Exception as e:
            db.rollback()
            return {
                "success": False,
                "message": f"Error creating task: {str(e)}"
            }
