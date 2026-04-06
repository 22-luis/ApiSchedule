import logging
import uuid
from datetime import datetime, time, timedelta, date
from typing import List, Dict, Any, Optional

from sqlalchemy.orm import Session

from app.modules.codes.models.code import Code
from app.shared.utils.core.time_utils import TimeZoneUtils
from app.modules.orders.models.order import Order
# from app.modules.programming.models.preparation import Preparation
from app.modules.programming.models.programming import Programming, ProgrammingTask
from app.modules.programming.models.state import ProgrammingStatus
from app.modules.programming.models.task import Task

logger = logging.getLogger(__name__)

class ProgrammingUtils:
    @staticmethod
    def extract_order_data(orders: List[Order]) -> List[Dict[str, Any]]:
        """
        Extrae datos básicos de una lista de órdenes.
        """
        # Debug logging to file
        try:
            with open("debug_automation.log", "a") as f:
                f.write(f"[{TimeZoneUtils.get_now()}] extract_order_data called with {len(orders) if orders else 0} orders\n")
                if orders:
                    for i, o in enumerate(orders):
                        f.write(f"  Order {i}: Lote={o.lote}, Code={o.code}, Qty={o.quantity}, Bin={o.bin}\n")
                else:
                    f.write("  Orders list is empty or None\n")
        except ValueError:
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
            with open("debug_automation.log", "a") as f:
                f.write(f"[{TimeZoneUtils.get_now()}] extracted_data result: {len(extracted_data)} items\n")
        except ValueError:
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
        # Usamos la información del código directamente, ya que Preparation no tiene la info necesaria
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
                # Adaptar estructura para que coincida con lo esperado por los servicios.
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
            
        # For now, using the Code model directly as Preparation is commented out
        if code_obj.activity == activity_name:
            return {
                "success": True,
                "activity_details": {
                    "activity": code_obj.activity,
                    "performance": code_obj.performance,
                    "time": code_obj.time,
                    "preparation_id": code_obj.id, # Using code_obj.id as a reference
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
        
        # --- AUTO-CREATE LOGIC START ---
        # Si no hay programaciones o la primera está muy lejos (> 7 días), creamos una automáticamente
        target_date = start_date if start_date else (date.today() + timedelta(days=1))
        should_create = False
        
        if not programmings:
            should_create = True
            logger.info(f"No programmings found for team {team_id}. Auto-creating for {target_date}")
        else:
            # Chequear si la primera fecha está muy lejos
            first_prog_date = programmings[0].date
            days_diff = (first_prog_date - target_date).days
            
            # FIXED: stricter check. If there is ANY gap (days_diff > 0), auto-create the target date.
            # This ensures we don't skip empty days just because a future one exists.
            if days_diff > 0:
                should_create = True
                logger.info(f"First programming is {days_diff} days away ({first_prog_date}). Auto-creating for {target_date} to fill gap.")

        if should_create:
            try:
                # Importación local para evitar ciclos si los hubiera, aunque están en el mismo módulo
                from app.modules.automation.services.utils.auto_create_programming import create_programming_if_not_exists
                
                creation_result = create_programming_if_not_exists(db, team_id, target_date)
                if creation_result.get("success") and creation_result.get("created"):
                    logger.info(f"Auto-created programming check successful: {creation_result.get('message')}")
                    # Re-ejecutar la query para incluir la nueva programacion
                    # Re-instance query porque SQLAlchemy query objects son mutables pero mejor ir a lo seguro
                    query = db.query(Programming).filter(
                        Programming.team_id == team_id,
                        Programming.status == ProgrammingStatus.available
                    )
                    if start_date:
                        query = query.filter(Programming.date >= start_date)
                    programmings = query.order_by(Programming.date).all()
            except Exception as e:
                logger.error(f"Failed to auto-create programming inside get_available_programmings_for_team: {e}")
        # --- AUTO-CREATE LOGIC END ---
        
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
    def adjust_for_lunch_break(start_dt: datetime, duration_minutes: int) -> datetime:
        """
        Ajusta el tiempo de finalización considerando el descanso de almuerzo (12:00 PM - 1:00 PM).
        Si la tarea cruza las 12:00 PM, se extiende 60 minutos.
        Si la tarea inicia durante el almuerzo, se mueve el inicio a la 1:00 PM.
        """
        # 12:00 PM = 720 minutos, 1:00 PM = 780 minutos desde la medianoche
        start_minutes = start_dt.hour * 60 + start_dt.minute
        
        # Caso 1: Inicia antes de las 12 y terminaría después de las 12
        if start_minutes < 720:
            if start_minutes + duration_minutes > 720:
                return start_dt + timedelta(minutes=duration_minutes + 60)
            else:
                return start_dt + timedelta(minutes=duration_minutes)
        
        # Caso 2: Inicia durante el almuerzo (12:00 - 13:00)
        elif 720 <= start_minutes < 780:
            # Mover el inicio a las 1:00 PM y sumar la duración
            start_date = start_dt.date()
            new_start = datetime.combine(start_date, time(13, 0))
            return new_start + timedelta(minutes=duration_minutes)
            
        # Caso 3: Inicia después del almuerzo
        else:
            return start_dt + timedelta(minutes=duration_minutes)

    @staticmethod
    def calculate_current_programming_time(programming_tasks: List[ProgrammingTask], programming_date: date) -> int:
        """
        Calcula el tiempo ocupado actual de una programación en minutos desde la medianoche.
        Si no hay tareas, devuelve el tiempo de inicio estándar.
        """
        # Horarios estándar de inicio
        is_saturday = programming_date.weekday() == 5
        standard_start_minutes = 450 if is_saturday else 420  # 7:30 AM o 7:00 AM

        if not programming_tasks:
            return standard_start_minutes

        # Encontrar el tiempo de finalización más tardío
        max_end_minutes = standard_start_minutes
        
        # Intentar importar timezone para manejar conversiones si es necesario
        try:
            from pytz import timezone
            sv_tz = timezone("America/El_Salvador")
        except ImportError:
            sv_tz = None

        for pt in programming_tasks:
            if pt.end_time:
                # Asegurar que estamos trabajando con tiempo local
                end_time = pt.end_time
                if sv_tz and end_time.tzinfo is not None:
                    end_time = end_time.astimezone(sv_tz).replace(tzinfo=None)
                
                # Convertir a minutos desde la medianoche
                current_minutes = end_time.hour * 60 + end_time.minute
                if current_minutes > max_end_minutes:
                    max_end_minutes = current_minutes
        
        return max_end_minutes

    @staticmethod
    def create_order_task(programming_id: str, programming_tasks: List[ProgrammingTask], task_minutes: int, 
                         order_data: Dict, activity_details: Dict, db: Session,
                         override_start_time: Optional[datetime] = None,
                         override_end_time: Optional[datetime] = None) -> Dict[str, Any]:
        """
        Crea una tarea de programación para una orden.
        """
        try:
            # Obtener la fecha de la programación
            programming = db.query(Programming).filter(Programming.id == programming_id).first()
            if not programming:
                return {
                    "success": False,
                    "message": "Programming not found"
                }
            
            # Asegurar que programming_date sea de tipo date para evitar warnings de tipo
            programming_date: date = programming.date

            if override_start_time and override_end_time:
                start_datetime = override_start_time
                end_datetime = override_end_time
            else:
                # Calcular hora de inicio basada en tareas existentes
                start_minutes = ProgrammingUtils.calculate_current_programming_time(programming_tasks, programming_date)
                
                # Convertir minutos a datetime para el ajuste
                start_hour = start_minutes // 60
                start_minute = start_minutes % 60
                start_datetime = datetime.combine(programming_date, time(start_hour, start_minute))
                
                # Usar la nueva utilidad para calcular el end_datetime con el ajuste de almuerzo
                end_datetime = ProgrammingUtils.adjust_for_lunch_break(start_datetime, task_minutes)
                
                # Re-ajustar start_datetime por si acaso el inicio cayó en el almuerzo
                # (El método adjust_for_lunch_break no muta el inicio original, así que si cayó en almuerzo, 
                # necesitamos asegurar que el start_datetime guardado sea el correcto)
                start_total_mins = start_datetime.hour * 60 + start_datetime.minute
                if 720 <= start_total_mins < 780:
                     start_datetime = datetime.combine(programming_date, time(13, 0))
            
            task_id = uuid.uuid4()
            next_order = order_data.get("lote")

            # Crear la tarea principal
            new_task = Task(
                id=task_id,
                code_id=activity_details.get("code_id"),
                lote=str(order_data.get("lote")),
                # Guardar el lote original de empaque si existe (para órdenes bin 8)
                original_packaging_lote=str(order_data.get("original_packaging_lote")) if order_data.get("original_packaging_lote") else None,
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
