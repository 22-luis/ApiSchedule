"""
Servicio para la creación y gestión de tareas de pesado cuando se agregan órdenes.
"""
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from datetime import datetime, timedelta, time, date
import math

from app.models.team import Team
from app.models.programming import Programming, ProgrammingStatus
from app.models.programming import ProgrammingTask
from app.models.task import Task
from app.models.code import Code


class WeighingTaskService:
    """Servicio para manejar la creación de tareas de pesado"""
    
    # Configuración de límites de tiempo
    TIME_LIMIT = time(17, 40)  # 17:40
    TOLERANCE_MINUTES = 5
    MAX_ALLOWED_MINUTES = TIME_LIMIT.hour * 60 + TIME_LIMIT.minute + TOLERANCE_MINUTES
    
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
            activities_data = WeighingTaskService.get_activities_by_code(code, db)
            activities_by_code[code] = activities_data
        
        return {
            "activities_by_code": activities_by_code,
            "total_codes_processed": len(unique_codes),
            "codes_processed": list(unique_codes)
        }
    
    @staticmethod
    def filter_weighing_activities(activities_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Filtra las actividades para obtener solo las relacionadas con pesado.
        
        Args:
            activities_data: Diccionario con todas las actividades organizadas por código
            
        Returns:
            Diccionario con solo las actividades de pesado organizadas por código
        """
        weighing_activities_by_code = {}
        
        activities_by_code = activities_data.get("activities_by_code", {})
        for code, code_data in activities_by_code.items():
            activities = code_data.get("activities", [])
            weighing_activities = []
            
            for activity in activities:
                activity_name = activity.get("activity", "").upper()
                
                # Buscar actividades relacionadas con pesado
                if any(keyword in activity_name for keyword in ["PESADO", "PESAR", "PESO", "BALANZA", "WEIGHING"]):
                    weighing_activities.append(activity)
            
            if weighing_activities:
                weighing_activities_by_code[code] = {
                    "code": code,
                    "weighing_activities": weighing_activities,
                    "total_weighing_activities": len(weighing_activities),
                    "found": True
                }
        
        return {
            "weighing_activities_by_code": weighing_activities_by_code,
            "total_codes_with_weighing": len(weighing_activities_by_code),
            "codes_with_weighing": list(weighing_activities_by_code.keys())
        }
    
    @staticmethod
    def calculate_minutes_from_performance_and_quantity(performance: float, quantity: int) -> int:
        """
        Calcula los minutos multiplicando performance (en horas) con la cantidad de la orden.
        
        Args:
            performance: Rendimiento de la actividad en horas
            quantity: Cantidad de la orden
            
        Returns:
            Minutos calculados (entero con ceiling)
        """
        if performance is None or quantity is None:
            return 0
        
        # Calcular horas: performance * quantity
        hours = performance * quantity
        
        # Convertir horas a minutos y aplicar ceiling
        minutes = hours * 60
        return math.ceil(minutes)
    
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
    def get_weighing_activities_with_minutes(extracted_orders: List[Dict], db: Session) -> Dict[str, Any]:
        """
        Obtiene las actividades de pesado para todas las órdenes extraídas y calcula los minutos.
        
        Args:
            extracted_orders: Lista de órdenes extraídas (con lote, quantity, code)
            db: Sesión de base de datos
            
        Returns:
            Diccionario con actividades de pesado y minutos calculados
        """
        # Obtener todas las actividades
        all_activities = WeighingTaskService.get_activities_for_orders(extracted_orders, db)
        
        # Filtrar solo las de pesado
        weighing_activities = WeighingTaskService.filter_weighing_activities(all_activities)
        
        # Calcular minutos para cada actividad de pesado
        weighing_activities_with_minutes = {}
        weighing_activities_by_code = weighing_activities.get("weighing_activities_by_code", {})
        
        for code, code_data in weighing_activities_by_code.items():
            weighing_activities_list = code_data.get("weighing_activities", [])
            activities_with_minutes = []
            
            for activity_data in weighing_activities_list:
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
                        calculated_minutes = WeighingTaskService.calculate_minutes_from_performance_and_quantity(
                            performance, order_quantity
                        )
                        
                        # Calcular horas para mostrar en la fórmula
                        hours_calculation = performance * order_quantity
                        
                        activities_with_minutes.append({
                            "activity_data": activity_data,
                            "minutes_calculation": {
                                "performance": performance,
                                "quantity": order_quantity,
                                "hours_calculation": hours_calculation,
                                "calculated_minutes": calculated_minutes,
                                "formula": f"{performance} horas * {order_quantity} = {hours_calculation} horas * 60 = {calculated_minutes} minutos (con ceiling)"
                            }
                        })
            
            if activities_with_minutes:
                weighing_activities_with_minutes[code] = {
                    "code": code,
                    "weighing_activities_with_minutes": activities_with_minutes,
                    "total_weighing_activities": len(activities_with_minutes),
                    "found": True
                }
        
        return {
            "all_activities": all_activities,
            "weighing_activities": weighing_activities,
            "weighing_activities_with_minutes": {
                "weighing_activities_with_minutes_by_code": weighing_activities_with_minutes,
                "total_codes_with_weighing_minutes": len(weighing_activities_with_minutes),
                "codes_with_weighing_minutes": list(weighing_activities_with_minutes.keys())
            },
            "total_orders_processed": len(extracted_orders)
        }
    
    @staticmethod
    def get_most_suitable_weighing_team(db: Session) -> Dict[str, Any]:
        """
        Obtiene el equipo más idóneo para actividades de pesado.
        
        Args:
            db: Sesión de base de datos
            
        Returns:
            Diccionario con información del equipo más idóneo para pesado
        """
        # Buscar equipos que contengan "pesado" en el nombre
        weighing_teams = db.query(Team).filter(Team.name.ilike('%pesado%')).all()
        
        if not weighing_teams:
            return {
                "success": False,
                "message": "No se encontraron equipos de pesado en la base de datos",
                "weighing_teams": [],
                "most_suitable_team": None
            }
        
        # Lógica para determinar el equipo más idóneo
        most_suitable_team = None
        
        # Buscar "pesado principal"
        for team in weighing_teams:
            if "principal" in team.name.lower():
                most_suitable_team = team
                break
        
        # Si no hay principal, buscar "pesado 1"
        if not most_suitable_team:
            for team in weighing_teams:
                if "pesado 1" in team.name.lower() or "pesado1" in team.name.lower():
                    most_suitable_team = team
                    break
        
        # Si no hay ninguno específico, tomar el primero
        if not most_suitable_team and weighing_teams:
            most_suitable_team = weighing_teams[0]
        
        if most_suitable_team:
            return {
                "success": True,
                "message": f"Equipo más idóneo para pesado encontrado: {most_suitable_team.name}",
                "weighing_teams": [
                    {
                        "id": str(team.id),
                        "name": team.name,
                        "is_most_suitable": team.id == most_suitable_team.id
                    } for team in weighing_teams
                ],
                "most_suitable_team": {
                    "id": str(most_suitable_team.id),
                    "name": most_suitable_team.name,
                    "supervisor_id": str(most_suitable_team.supervisorId) if most_suitable_team.supervisorId else None
                },
                "total_weighing_teams": len(weighing_teams)
            }
        else:
            return {
                "success": False,
                "message": "No se pudo determinar el equipo más idóneo para pesado",
                "weighing_teams": [],
                "most_suitable_team": None
            }
    
    @staticmethod
    def get_available_programmings_for_team(team_id: str, db: Session) -> List[Dict[str, Any]]:
        """
        Obtiene las programaciones disponibles para un equipo específico.
        Devuelve todas las programaciones futuras ordenadas por fecha (más cercana primero).
        
        Args:
            team_id: ID del equipo
            db: Sesión de base de datos
            
        Returns:
            Lista de programaciones disponibles ordenadas por fecha
        """
        current_date = date.today()
        
        # DEBUG: Buscar TODAS las programaciones del equipo (sin filtro de status)
        all_programmings = (
            db.query(Programming)
            .filter(
                Programming.team_id == team_id,
                Programming.date >= current_date
            )
            .order_by(Programming.date)
            .all()
        )
        
        print(f"🔍 DEBUG: Encontradas {len(all_programmings)} programaciones para equipo {team_id}")
        for prog in all_programmings:
            print(f"  📅 {prog.date} - Status: {prog.status} - Tareas: {len(prog.programming_tasks) if prog.programming_tasks else 0}")
        
        # Buscar programaciones disponibles ordenadas por fecha (más cercana primero)
        available_programmings = (
            db.query(Programming)
            .filter(
                Programming.team_id == team_id,
                Programming.date >= current_date,
                Programming.status == ProgrammingStatus.available
            )
            .order_by(Programming.date)
            .all()
        )
        
        print(f"✅ DEBUG: Programaciones disponibles (status=available): {len(available_programmings)}")
        for prog in available_programmings:
            print(f"  ✅ {prog.date} - Status: {prog.status}")
        
        # Si no hay programaciones disponibles, crear una nueva
        if not available_programmings:
            print("⚠️ DEBUG: No hay programaciones disponibles, creando nueva...")
            new_programmings = WeighingTaskService._create_new_programming(team_id, db)
            if new_programmings:
                available_programmings = new_programmings
                print(f"🆕 DEBUG: Nueva programación creada: {new_programmings[0].date}")
        
        # Preparar datos de programaciones con información adicional
        programming_data = []
        for programming in available_programmings:
            # Calcular días hasta la programación
            days_until = (programming.date - current_date).days
            is_current_month = programming.date.month == current_date.month and programming.date.year == current_date.year
            
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
        
        print(f"📊 DEBUG: Retornando {len(programming_data)} programaciones")
        for prog_info in programming_data:
            print(f"  📋 {prog_info['date']} - Status: {prog_info['status']} - Tareas: {prog_info['total_tasks']}")
        
        return programming_data
    
    @staticmethod
    def _create_new_programming(team_id: str, db: Session) -> List[Programming]:
        """
        Crea una nueva programación para el equipo usando fechas más cercanas.
        Busca huecos en las programaciones existentes.
        
        Args:
            team_id: ID del equipo
            db: Sesión de base de datos
            
        Returns:
            Lista con la nueva programación creada
        """
        current_date = date.today()
        
        # Buscar programaciones existentes del equipo ordenadas por fecha
        existing_programmings = (
            db.query(Programming)
            .filter(Programming.team_id == team_id)
            .order_by(Programming.date)
            .all()
        )
        
        # Buscar el primer hueco disponible en las próximas 30 días
        start_date = current_date + timedelta(days=1)  # Empezar desde mañana
        end_date = current_date + timedelta(days=30)   # Buscar hasta 30 días
        
        # Crear lista de fechas disponibles
        available_dates = []
        current_check_date = start_date
        
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
    def verify_programming_time_limit(programmings: List[Dict], task_minutes: int, db: Session, 
                                    order_data: Optional[Dict] = None, 
                                    activity_details: Optional[Dict] = None) -> Dict[str, Any]:
        print(f"🔍 DEBUG: verify_programming_time_limit recibió task_minutes: {task_minutes}")
        """
        Verifica que al agregar una tarea a una programación no se exceda el límite de tiempo.
        Evalúa programaciones secuencialmente desde la más cercana hasta la más lejana.
        
        Args:
            programmings: Lista de programaciones disponibles ordenadas por fecha
            task_minutes: Minutos de la tarea a agregar
            db: Sesión de base de datos
            order_data: Datos de la orden (opcional)
            activity_details: Detalles de la actividad (opcional)
            
        Returns:
            Resultado de la verificación con programación seleccionada
        """
        current_date = date.today()
        
        # Asegurar que las programaciones estén ordenadas por fecha (más cercana primero)
        sorted_programmings = sorted(
            programmings,
            key=lambda p: (
                datetime.strptime(p.get("date", "9999-12-31"), "%Y-%m-%d").date() - current_date
            ).days
        )
        
        # Evaluar cada programación secuencialmente
        for programming in sorted_programmings:
            programming_id = programming.get("id")
            programming_date = programming.get("date")
            
            print(f"🔍 Evaluando programación: {programming_date}")
            
            # Verificar que la programación esté en fecha actual o futura
            try:
                programming_date_obj = datetime.strptime(programming_date, "%Y-%m-%d").date()
                if programming_date_obj < current_date:
                    continue
            except:
                continue
            
            # Obtener la programación completa de la base de datos
            programming_obj = db.query(Programming).filter(Programming.id == programming_id).first()
            if not programming_obj:
                continue
            
            # Verificar que la programación esté disponible
            if programming_obj.status != ProgrammingStatus.available:
                print(f"  ❌ Rechazada: Status no disponible ({programming_obj.status})")
                continue
            
            # Obtener las tareas de la programación
            programming_tasks = db.query(ProgrammingTask).filter(
                ProgrammingTask.programming_id == programming_id
            ).all()
            
            # Calcular el tiempo actual de la programación
            current_end_minutes = WeighingTaskService._calculate_current_programming_time(
                programming_tasks, programming_date_obj
            )
            
            # DEBUG: Mostrar detalles de las tareas
            print(f"  🔍 DEBUG: {len(programming_tasks)} tareas en programación")
            for i, programming_task in enumerate(programming_tasks):
                start_str = programming_task.start_time.strftime("%H:%M") if programming_task.start_time else "N/A"
                end_str = programming_task.end_time.strftime("%H:%M") if programming_task.end_time else "N/A"
                start_raw = str(programming_task.start_time) if programming_task.start_time else "N/A"
                end_raw = str(programming_task.end_time) if programming_task.end_time else "N/A"
                print(f"    Tarea {i+1}: {start_str} - {end_str}")
                print(f"      Raw start: {start_raw}")
                print(f"      Raw end: {end_raw}")
                # Obtener minutos de la tarea relacionada
                existing_task_minutes = None
                if hasattr(programming_task, 'task') and programming_task.task:
                    existing_task_minutes = programming_task.task.minutes
                print(f"      Minutos: {existing_task_minutes if existing_task_minutes else 'N/A'}")
            print(f"  📊 Tiempo calculado: {current_end_minutes} minutos ({current_end_minutes//60:02d}:{current_end_minutes%60:02d})")
            
            # Calcular el tiempo final si se agrega la nueva tarea
            final_minutes = current_end_minutes + task_minutes
            
            print(f"  📊 Tiempo actual: {current_end_minutes} min, Nueva tarea: {task_minutes} min, Final: {final_minutes} min, Límite: {WeighingTaskService.MAX_ALLOWED_MINUTES} min")
            
            # Verificar si se excede el límite de tiempo
            if final_minutes <= WeighingTaskService.MAX_ALLOWED_MINUTES:
                # Obtener información del equipo
                team_obj = db.query(Team).filter(Team.id == programming_obj.team_id).first()
                team_name = team_obj.name if team_obj else "Equipo desconocido"
                
                result = {
                    "success": True,
                    "message": f"Programación seleccionada: {programming_date} - Cumple con límite de tiempo",
                    "selected_programming": {
                        "id": programming_id,
                        "date": programming_date,
                        "team_id": str(programming_obj.team_id),
                        "team_name": team_name,
                        "task_minutes": task_minutes,  # Este es el parámetro original
                        "time_limit": WeighingTaskService.TIME_LIMIT.isoformat(),
                        "tolerance_minutes": WeighingTaskService.TOLERANCE_MINUTES,
                        "current_tasks": len(programming_tasks),
                        "current_end_minutes": current_end_minutes,
                        "final_minutes": final_minutes
                    },
                    "verification_details": {
                        "current_end_minutes": current_end_minutes,
                        "final_minutes": final_minutes,
                        "max_allowed_minutes": WeighingTaskService.MAX_ALLOWED_MINUTES,
                        "within_limit": True,
                        "programming_date": programming_date,
                        "total_existing_tasks": len(programming_tasks)
                    }
                }
                
                # Crear la tarea de la orden si se proporcionaron los datos
                if order_data and activity_details:
                    task_result = WeighingTaskService._create_order_task(
                        programming_id, programming_tasks, task_minutes,  # Este es el parámetro original
                        order_data, activity_details, db
                    )
                    if task_result.get("success"):
                        result["order_task_created"] = task_result.get("task_data")
                
                print(f"  ✅ ACEPTADA: Cumple límite de tiempo")
                return result
            else:
                # Si se excede el límite, continuar con la siguiente programación
                print(f"  ❌ Rechazada: Excede límite de tiempo")
                continue
        
        # Si ninguna programación cumple con el límite
        return {
            "success": False,
            "message": "Ninguna programación disponible cumple con el límite de tiempo",
            "selected_programming": None,
            "evaluated_programmings": len(sorted_programmings)
        }
    
    @staticmethod
    def _calculate_current_programming_time(programming_tasks: List[ProgrammingTask], 
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
            # Programación vacía - usar 7:00 AM como tiempo base
            return 7 * 60
        
        # Sumar los minutos de todas las tareas
        total_minutes = 0
        valid_tasks = []
        
        print(f"    🔍 DEBUG CÁLCULO - SUMANDO MINUTOS DE TAREAS:")
        
        for programming_task in programming_tasks:
            # Obtener la tarea asociada para acceder a los minutos
            task_minutes = None
            if hasattr(programming_task, 'task') and programming_task.task:
                task_minutes = programming_task.task.minutes
                print(f"      Tarea ID: {programming_task.task_id}, minutos: {task_minutes}")
            else:
                print(f"      Tarea ID: {programming_task.task_id}, sin relación task")
            
            if task_minutes is not None and task_minutes > 0:
                total_minutes += task_minutes
                valid_tasks.append(programming_task)
                print(f"      ✅ Tarea: {task_minutes} minutos (total acumulado: {total_minutes})")
            else:
                print(f"      ❌ Tarea: minutos no válidos ({task_minutes}) - ignorada")
        
        if valid_tasks:
            print(f"      📊 Total de minutos sumados: {total_minutes} ({total_minutes//60:02d}:{total_minutes%60:02d})")
            return total_minutes
        else:
            # Si no hay tareas con minutos válidos, usar 7:00 AM
            print(f"      ⚠️ No hay tareas con minutos válidos, usando 7:00 AM como base")
            return 7 * 60
    
    @staticmethod
    def _create_order_task(programming_id: str, programming_tasks: List[ProgrammingTask], 
                          task_minutes: int, order_data: Dict, activity_details: Dict, 
                          db: Session) -> Dict[str, Any]:
        print(f"🔍 DEBUG: _create_order_task recibió task_minutes: {task_minutes}")
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
        try:
            # Obtener la fecha de la programación
            programming_obj = db.query(Programming).filter(Programming.id == programming_id).first()
            programming_date = programming_obj.date if programming_obj else date.today()
            
            # Calcular start_time y end_time para la nueva tarea
            current_end_minutes = WeighingTaskService._calculate_current_programming_time(
                programming_tasks, programming_date
            )
            
            # Crear datetime para start_time usando la fecha de la programación
            task_start_time = datetime.combine(
                programming_date,
                time(hour=current_end_minutes // 60, minute=current_end_minutes % 60)
            )
            
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
            db.commit()
            db.refresh(order_task_obj)
            db.refresh(order_programming_task)
            
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
            
        except Exception as e:
            db.rollback()
            return {
                "success": False,
                "error": str(e)
            }
    
    @staticmethod
    def create_weighing_tasks_for_orders(extracted_orders: List[Dict], db: Session) -> Dict[str, Any]:
        """
        Función principal que maneja todo el proceso de creación de tareas de pesado.
        
        Args:
            extracted_orders: Lista de órdenes extraídas con lote, quantity y code
            db: Sesión de base de datos
        
        Returns:
            Resultado del proceso con información de las tareas creadas
        """
        try:
            # Obtener actividades de pesado con minutos calculados
            weighing_activities_data = WeighingTaskService.get_weighing_activities_with_minutes(
                extracted_orders, db
            )
            
            # Obtener equipo más idóneo para pesado
            team_result = WeighingTaskService.get_most_suitable_weighing_team(db)
            
            if not team_result.get("success"):
                return {
                    "success": False,
                    "message": "No se pudo obtener equipo idóneo para pesado",
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
            
            # Obtener programaciones disponibles
            available_programmings = WeighingTaskService.get_available_programmings_for_team(team_id, db)
            
            if not available_programmings:
                return {
                    "success": False,
                    "message": "No se encontraron programaciones disponibles para el equipo de pesado",
                    "tasks_created": 0,
                    "total_orders": len(extracted_orders)
                }
            
            # Procesar cada orden
            created_tasks = []
            failed_orders = []
            
            for order_data in extracted_orders:
                # Obtener la actividad de pesado específica para esta orden
                pesado_activity = WeighingTaskService._get_pesado_activity_for_order(
                    order_data, weighing_activities_data
                )
                
                if not pesado_activity:
                    failed_orders.append({
                        "order_data": order_data,
                        "reason": "No se encontró actividad de pesado válida"
                    })
                    continue
                
                task_minutes = pesado_activity.get("minutes_calculation", {}).get("calculated_minutes", 0)
                activity_details = pesado_activity.get("activity_data", {})
                
                print(f"🔍 DEBUG: Minutos calculados para orden {order_data.get('lote')}: {task_minutes}")
                print(f"🔍 DEBUG: Actividad: {activity_details.get('activity')}")
                print(f"🔍 DEBUG: Performance: {activity_details.get('performance')}")
                print(f"🔍 DEBUG: Cantidad: {order_data.get('quantity')}")
                
                if task_minutes <= 0:
                    failed_orders.append({
                        "order_data": order_data,
                        "reason": "Los minutos calculados no son válidos"
                    })
                    continue
                
                print(f"🔍 DEBUG: Antes de verify_programming_time_limit - task_minutes: {task_minutes}")
                
                # Verificar límite de tiempo y crear tarea
                time_verification = WeighingTaskService.verify_programming_time_limit(
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
                "weighing_activities_data": weighing_activities_data
            }
            
        except Exception as e:
            return {
                "success": False,
                "message": f"Error durante la creación de tareas de pesado: {str(e)}",
                "tasks_created": 0,
                "total_orders": len(extracted_orders)
            }
    
    @staticmethod
    def _get_pesado_activity_for_order(order_data: Dict, weighing_activities_data: Dict) -> Optional[Dict]:
        """
        Obtiene la actividad de pesado específica para una orden.
        
        Args:
            order_data: Datos de la orden (lote, quantity, code)
            weighing_activities_data: Datos de actividades de pesado con minutos calculados
            
        Returns:
            Actividad de pesado específica para la orden o None si no se encuentra
        """
        order_code = order_data.get('code')
        if not order_code:
            return None
        
        # Buscar las actividades para el código de esta orden
        code_data = weighing_activities_data.get("weighing_activities_with_minutes", {}).get(
            "weighing_activities_with_minutes_by_code", {}
        ).get(order_code)
        
        if not code_data or not code_data.get("weighing_activities_with_minutes"):
            return None
        
        # Buscar específicamente la actividad "PESADO"
        pesado_activity = None
        for activity in code_data["weighing_activities_with_minutes"]:
            activity_name = activity.get("activity_data", {}).get("activity", "")
            if activity_name and "PESADO" in activity_name.upper():
                pesado_activity = activity
                break
        
        # Si no se encuentra "PESADO", usar la primera actividad disponible
        if not pesado_activity:
            pesado_activity = code_data["weighing_activities_with_minutes"][0]
        
        return pesado_activity
