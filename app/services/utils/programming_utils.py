"""
Utilidades comunes para programación de tareas.
Contiene funciones compartidas entre diferentes servicios de tareas.
"""

from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from datetime import datetime, timedelta, time, date

from app.models.team import Team
from app.models.programming import Programming, ProgrammingStatus
from app.models.programming import ProgrammingTask
from app.models.task import Task
from app.models.code import Code


class ProgrammingUtils:
    """Utilidades comunes para programación de tareas"""
    
    @staticmethod
    def extract_order_data(orders: List) -> List[Dict[str, Any]]:
        """
        Extrae solo los campos lote, quantity y code de las órdenes.
        
        Args:
            orders: Lista de objetos Order de la base de datos
            
        Returns:
            Lista de diccionarios con solo lote, quantity y code
        """
        extracted_data = []
        
        for order in orders:
            order_data = {
                "lote": order.lote,
                "quantity": order.quantity,
                "code": order.code
            }
            extracted_data.append(order_data)
        
        return extracted_data
    
    @staticmethod
    def get_activities_by_code(code: str, db: Session) -> Dict[str, Any]:
        """
        Obtiene todas las actividades para un código específico.
        
        Args:
            code: Código de la orden
            db: Sesión de base de datos
            
        Returns:
            Diccionario con las actividades del código
        """
        code_objs = db.query(Code).filter(Code.code == code).all()
        
        if not code_objs:
            return {
                "code": code,
                "activities": [],
                "total_activities": 0,
                "found": False
            }
        
        activities = []
        for code_obj in code_objs:
            activity_data = {
                "id": str(code_obj.id),
                "activity": getattr(code_obj, "activity", None),
                "description": getattr(code_obj, "description", None),
                "unit": getattr(code_obj, "unit", None),
                "type": getattr(code_obj, "type", None),
                "quantity": getattr(code_obj, "quantity", None),
                "time": getattr(code_obj, "time", None),
                "people": getattr(code_obj, "people", None),
                "performance": getattr(code_obj, "performance", None),
                "material": getattr(code_obj, "material", None),
                "presentation": getattr(code_obj, "presentation", None),
                "fabricationCode": getattr(code_obj, "fabricationCode", None),
                "usefulLife": getattr(code_obj, "usefulLife", None)
            }
            activities.append(activity_data)
        
        return {
            "code": code,
            "activities": activities,
            "total_activities": len(activities),
            "found": True
        }
    
    @staticmethod
    def get_activities_for_orders(extracted_orders: List[Dict], db: Session) -> Dict[str, Any]:
        """
        Obtiene las actividades para todas las órdenes extraídas.
        
        Args:
            extracted_orders: Lista de órdenes extraídas (con lote, quantity, code)
            db: Sesión de base de datos
            
        Returns:
            Diccionario con actividades organizadas por código
        """
        activities_by_code = {}
        unique_codes = set()
        
        for order in extracted_orders:
            code = order.get('code')
            if code:
                unique_codes.add(code)
        
        for code in unique_codes:
            activities_data = ProgrammingUtils.get_activities_by_code(code, db)
            activities_by_code[code] = activities_data
        
        return {
            "activities_by_code": activities_by_code,
            "total_codes_processed": len(unique_codes),
            "codes_processed": list(unique_codes)
        }
    
    @staticmethod
    def get_activity_details_by_code_and_activity(code: str, activity: str, db: Session) -> Dict[str, Any]:
        """
        Obtiene los datos detallados de una actividad específica.
        
        Args:
            code: Código del producto
            activity: Nombre de la actividad
            db: Sesión de base de datos
            
        Returns:
            Diccionario con los datos detallados de la actividad
        """
        code_obj = db.query(Code).filter(Code.code == code, Code.activity == activity).first()
        
        if not code_obj:
            return {
                "success": False,
                "code": code,
                "activity": activity,
                "activity_details": None,
                "message": f"No se encontró código '{code}' con actividad '{activity}'"
            }
        
        activity_details = {
            "id": str(code_obj.id),
            "code": code_obj.code,
            "activity": code_obj.activity,
            "specification": code_obj.description,
            "people": code_obj.people,
            "performance": code_obj.performance,
            "material": code_obj.material,
            "presentation": code_obj.presentation,
            "fabricationCode": code_obj.fabricationCode,
            "usefulLife": code_obj.usefulLife,
            "unit": code_obj.unit,
            "type": code_obj.type,
            "description": code_obj.description,
            "quantity": code_obj.quantity,
            "time": code_obj.time
        }
        
        return {
            "success": True,
            "code": code,
            "activity": activity,
            "activity_details": activity_details,
            "message": f"Datos obtenidos exitosamente para código '{code}' y actividad '{activity}'"
        }
    
    @staticmethod
    def get_available_programmings_for_team(team_id: str, db: Session, start_date: Optional[date] = None) -> List[Dict[str, Any]]:
        """
        Obtiene las programaciones disponibles para un equipo específico.
        Devuelve todas las programaciones futuras a partir de start_date, ordenadas por fecha.
        
        Args:
            team_id: ID del equipo
            db: Sesión de base de datos
            start_date: Fecha de inicio para la búsqueda (opcional)
            
        Returns:
            Lista de programaciones disponibles ordenadas por fecha
        """
        search_date = start_date if start_date else date.today()
        
        # Buscar programaciones disponibles ordenadas por fecha (más cercana primero)
        available_programmings = (
            db.query(Programming)
            .filter(
                Programming.team_id == team_id,
                Programming.date >= search_date,
                Programming.status == ProgrammingStatus.available
            )
            .order_by(Programming.date)
            .all()
        )
        
        # Si no hay programaciones disponibles, crear una nueva
        if not available_programmings:
            new_programmings = ProgrammingUtils._create_new_programming(team_id, db, start_date=search_date)
            if new_programmings:
                available_programmings = new_programmings
        
        # Preparar datos de programaciones con información adicional
        programming_data = []
        for programming in available_programmings:
            # Calcular días hasta la programación
            days_until = (programming.date - search_date).days
            is_current_month = programming.date.month == search_date.month and programming.date.year == search_date.year
            
            programming_info = {
                "id": str(programming.id),
                "date": programming.date.isoformat(),
                "status": programming.status.value if programming.status else "available",
                "team_id": str(programming.team_id),
                "total_tasks": len(programming.programming_tasks) if programming.programming_tasks else 0,
                "is_newly_created": programming in new_programmings if 'new_programmings' in locals() else False,
                "days_until": days_until,
                "is_current_month": is_current_month,
                "priority": "high" if is_current_month and days_until <= 7 else "normal"
            }
            programming_data.append(programming_info)
        
        return programming_data
    
    @staticmethod
    def _create_new_programming(team_id: str, db: Session, start_date: Optional[date] = None) -> List[Programming]:
        """
        Crea una nueva programación para el equipo usando fechas más cercanas.
                    import logging
        
                    logger = logging.getLogger(__name__)
        
                    # Primero intentar desde la fecha actual para priorizar programaciones de hoy
                    today = date.today()
                    logger.debug(f"get_available_programmings_for_team: team_id={team_id} requested_start_date={start_date} trying_today={today}")
        
                    search_date = today
        
        Args:
            team_id: ID del equipo
            db: Sesión de base de datos
            start_date: Fecha de inicio para la búsqueda (opcional)
            
        Returns:
            Lista con la nueva programación creada
        """
        current_date = start_date if start_date else date.today()
        
        # Buscar programaciones existentes del equipo ordenadas por fecha
        existing_programmings = (
            db.query(Programming)
            .filter(Programming.team_id == team_id)
            .order_by(Programming.date)
            .all()
        )
        
        # Buscar el primer hueco disponible en las próximas 30 días
        # Incluir la fecha 'current_date' como candidata (permitir crear programación en la misma fecha solicitada)
        search_start_date = current_date  # Empezar desde la fecha proporcionada (incluye hoy)
        end_date = current_date + timedelta(days=30)   # Buscar hasta 30 días
        
        # Crear lista de fechas disponibles
        available_dates = []
        current_check_date = search_start_date
        
        while current_check_date <= end_date:
            # Evitar domingos
            if current_check_date.weekday() != 6:
                # Verificar si ya existe una programación para esta fecha
                existing_programming = (
                    db.query(Programming)
                    .filter(Programming.team_id == team_id, Programming.date == current_check_date)
                    .first()
                )
                
                if not existing_programming:
                    available_dates.append(current_check_date)
            
            current_check_date += timedelta(days=1)
        
        # Si no hay fechas disponibles en los próximos 30 días, usar la lógica anterior
        if not available_dates:
            if existing_programmings:
                # Usar la fecha siguiente a la última programación
                last_programming = existing_programmings[-1]
                new_date = last_programming.date + timedelta(days=1)
            else:
                # Si no hay programaciones, empezar desde mañana
                new_date = current_date + timedelta(days=1)
            
            # Evitar domingos
            while new_date.weekday() == 6:
                new_date += timedelta(days=1)
            
            # Verificar que no exista ya una programación para esa fecha
            existing_programming = (
                db.query(Programming)
                .filter(Programming.team_id == team_id, Programming.date == new_date)
                .first()
            )
            
            if existing_programming:
                # Buscar la siguiente fecha disponible
                while existing_programming:
                    new_date += timedelta(days=1)
                    while new_date.weekday() == 6:
                        new_date += timedelta(days=1)
                    existing_programming = (
                        db.query(Programming)
                        .filter(Programming.team_id == team_id, Programming.date == new_date)
                        .first()
                    )
        else:
            # Usar la primera fecha disponible
            new_date = available_dates[0]
        
        # Crear la nueva programación
        new_programming = Programming(
            team_id=team_id,
            date=new_date,
            status=ProgrammingStatus.available
        )
        
        try:
            db.add(new_programming)
            db.commit()
            db.refresh(new_programming)
            return [new_programming]
        except Exception as e:
            db.rollback()
            return []
    
    @staticmethod
    def calculate_current_programming_time(programming_tasks: List[ProgrammingTask], 
                                         programming_date_obj: date) -> int:
        """
        Calcula el tiempo actual de una programación sumando los minutos de todas las tareas.
        
        Args:
            programming_tasks: Lista de tareas de la programación
            programming_date_obj: Fecha de la programación
            
        Returns:
            Minutos totales de todas las tareas de la programación
        """
        if not programming_tasks:
            # Programación completamente vacía
            return 0
        
        # Sumar los minutos de todas las tareas
        total_minutes = 0
        valid_tasks = []
        
        for programming_task in programming_tasks:
            # Obtener la tarea asociada para acceder a los minutos
            task_minutes = None
            if hasattr(programming_task, 'task') and programming_task.task:
                task_minutes = programming_task.task.minutes
            
            if task_minutes is not None and task_minutes > 0:
                total_minutes += task_minutes
                valid_tasks.append(programming_task)
        
        if valid_tasks:
            return total_minutes
        else:
            # Si no hay tareas con minutos válidos, programación vacía
            return 0
    
    @staticmethod
    def create_order_task(programming_id: str, programming_tasks: List[ProgrammingTask], 
                         task_minutes: int, order_data: Dict, activity_details: Dict, 
                         db: Session) -> Dict[str, Any]:
        """
        Crea la tarea de la orden en la programación.
        
        Args:
            programming_id: ID de la programación
            programming_tasks: Lista de tareas existentes
            task_minutes: Minutos de la tarea
            order_data: Datos de la orden
            activity_details: Detalles de la actividad
            db: Sesión de base de datos
            
        Returns:
            Resultado de la creación de la tarea
        """
        # Obtener la fecha de la programación
        programming_obj = db.query(Programming).filter(Programming.id == programming_id).first()
        programming_date = programming_obj.date if programming_obj else date.today()
        
        # Calcular start_time y end_time para la nueva tarea
        current_end_minutes = ProgrammingUtils.calculate_current_programming_time(
            programming_tasks, programming_date
        )
        
        # Si current_end_minutes es 0, la tarea empieza a las 7:00 AM (o 7:30 si es sábado).
        # Si no, se suma al tiempo de inicio del día.
        weekday = programming_date.weekday()
        if weekday == 5:  # Sábado
            start_of_day_time = time(hour=7, minute=30)
        else:
            start_of_day_time = time(hour=7, minute=0)

        start_of_day_datetime = datetime.combine(programming_date, start_of_day_time)
        
        task_start_time = start_of_day_datetime + timedelta(minutes=current_end_minutes)
        
        # Calcular end_time sumando los minutos
        task_end_time = task_start_time + timedelta(minutes=task_minutes)
        
        # Obtener el UUID del código específico para la actividad
        code_obj = db.query(Code).filter(
            Code.code == order_data.get('code'),
            Code.activity == activity_details.get('activity')
        ).first()
        code_id = code_obj.id if code_obj else None
        
        # Crear la tarea de la orden
        order_task_obj = Task(
            code_id=code_id,
            lote=str(order_data.get('lote')),
            quantity=order_data.get('quantity'),
            specification=activity_details.get('specification'),
            people=activity_details.get('people'),
            performance=activity_details.get('performance'),
            material=activity_details.get('material'),
            presentation=activity_details.get('presentation'),
            fabricationCode=activity_details.get('fabricationCode'),
            usefulLife=activity_details.get('usefulLife'),
            unit=activity_details.get('unit'),
            type=activity_details.get('type'),
            activity=activity_details.get('activity'),
            description=activity_details.get('description'),
            minutes=task_minutes,
            start_time=task_start_time,
            end_time=task_end_time
        )
        
        # Obtener el número de orden para la nueva tarea
        new_task_order = len(programming_tasks) + 1
        
        # Crear la asociación con la programación
        order_programming_task = ProgrammingTask(
            programming_id=programming_id,
            task_id=order_task_obj.id,
            order=new_task_order,
            start_time=task_start_time,
            end_time=task_end_time
        )
        
        # Agregar la tarea a la base de datos
        db.add(order_task_obj)
        db.flush()
        order_programming_task.task_id = order_task_obj.id
        db.add(order_programming_task)
        
        return {
            "success": True,
            "task_data": {
                "task_id": str(order_task_obj.id),
                "programming_id": str(order_programming_task.programming_id),
                "order": new_task_order,
                "start_time": task_start_time.isoformat(),
                "end_time": task_end_time.isoformat(),
                "minutes": task_minutes,
                "description": order_task_obj.description,
                "lote": order_task_obj.lote,
                "quantity": order_task_obj.quantity
            }
        }