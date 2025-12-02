"""
Utility functions for managing programming availability based on task end times and team types.
"""
from datetime import datetime, time, timedelta, date as date_class
from sqlalchemy.orm import Session
from app.modules.programming.models.programming import Programming, ProgrammingTask
from app.modules.core.models.team import Team
from app.modules.programming.models.state import ProgrammingStatus
from typing import Optional


def get_team_type(team: Team) -> str:
    """
    Returns the team type based on the name (substring, not exact).
    Example: 'fabricado 1', 'molino 2', 'pesado principal'...
    """
    name = (team.name or '').lower()
    if "fabricado" in name:
        return "fabricado"
    if "molino" in name:
        return "molino"
    if "pesado" in name:
        return "pesado"
    return "otro"


def get_cutoff_time_for_team(team: Team, date_obj: datetime.date = None) -> time:
    """
    Returns the cutoff time for a team based on its type and the day of the week.
    - Saturdays: 11:10 for all teams
    - Monday-Friday:
        - Pesado teams: 17:40
        - Other teams: 14:40
    """
    # If date is provided and it's Saturday (weekday 5), return 11:10
    if date_obj and date_obj.weekday() == 5:
        return time(11, 10)
        
    team_type = get_team_type(team)
    if team_type == "pesado":
        return time(17, 40)  # 17:40 for pesado teams
    else:
        return time(14, 40)  # 14:40 for other teams


# Duración estándar de la programación en minutos
STANDARD_DURATION_MINUTES = 460

# Reglas de equipos
# 'duration': duración máxima en minutos. None significa sin límite.
# Reglas de equipos
# 'duration': duración máxima en minutos. None significa sin límite.
TEAM_RULES = {
    "Molino": {
        "duration": STANDARD_DURATION_MINUTES
    },
    "Pesado": {
        "duration": None  # Sin límite de duración estándar
    },
    "Fabricado 1": {
        "duration": STANDARD_DURATION_MINUTES
    },
    "Fabricado 2": {
        "duration": STANDARD_DURATION_MINUTES
    },
    "Fabricado 3": {
        "duration": STANDARD_DURATION_MINUTES
    },
    "Empaque 1": {
        "duration": STANDARD_DURATION_MINUTES
    },
    "Empaque 2": {
        "duration": STANDARD_DURATION_MINUTES
    },
    "Empaque 3": {
        "duration": STANDARD_DURATION_MINUTES
    },
    "Empaque 4": {
        "duration": STANDARD_DURATION_MINUTES
    },
    "Maquina 1": {
        "duration": STANDARD_DURATION_MINUTES
    },
    "Maquina 2": {
        "duration": STANDARD_DURATION_MINUTES
    }
}


def get_team_rule(team_name: str) -> Optional[dict]:
    """
    Obtiene la regla del equipo permitiendo coincidencias flexibles.
    """
    if not team_name:
        return None
        
    # 1. Coincidencia exacta
    if team_name in TEAM_RULES:
        return TEAM_RULES[team_name]
    
    # 2. Coincidencia insensible a mayúsculas/minúsculas
    team_name_lower = team_name.lower()
    for key, rule in TEAM_RULES.items():
        if key.lower() == team_name_lower:
            return rule
            
    # 3. Coincidencia parcial para tipos conocidos
    if "pesado" in team_name_lower:
        return TEAM_RULES["Pesado"]
    if "molino" in team_name_lower:
        return TEAM_RULES["Molino"]
    # Para Fabricado, Empaque, Maquina, intentamos coincidir el número si existe
    # o fallback a una regla genérica si decidiéramos agregarla.
    # Por ahora, si es "Fabricado X" y no coincide arriba, quizás queramos
    # devolver la regla de Fabricado 1 como default?
    # Mejor mantener el comportamiento estricto para numerados para evitar errores,
    # pero "Pesado" es el crítico que suele tener nombres variados.
    
    return None


def check_programming_availability(db: Session, programming: Programming) -> bool:
    """
    Checks if a programming should be marked as unavailable based on:
    1. Date has passed (programming.date < current date)
    2. Programmable hours are filled (total scheduled time >= max allowed)
    3. Last task's end time exceeds cutoff time
    
    Returns True if the programming should be available, False if it should be unavailable.
    """
    # Check 1: Date has passed
    current_date = date_class.today()
    if programming.date < current_date:
        return False  # Past programming should be unavailable
    
    # Check 2: Programmable hours filled
    # Get all tasks in the programming to calculate total time
    programming_tasks = (
        db.query(ProgrammingTask)
        .filter(ProgrammingTask.programming_id == programming.id)
        .all()
    )
    
    if programming_tasks:
        # Get the team to determine max allowed duration
        team = db.query(Team).filter(Team.id == programming.team_id).first()
        if team:
            team_name = team.name
            
            # Determine max allowed minutes based on team rules
            team_rule = get_team_rule(team_name)
            if team_rule and "duration" in team_rule:
                duration_minutes = team_rule["duration"]
            else:
                duration_minutes = STANDARD_DURATION_MINUTES
            
            # Apply tolerance (10 minutes)
            tolerance_minutes = 10
            
            if duration_minutes is not None:
                max_allowed_minutes = duration_minutes + tolerance_minutes
                
                # Calculate current total time using the utility function
                from app.modules.programming.services.utils.programming_utils import ProgrammingUtils
                current_end_minutes = ProgrammingUtils.calculate_current_programming_time(
                    programming_tasks, programming.date
                )
                
                # Check if programmable hours are filled
                if current_end_minutes >= max_allowed_minutes:
                    return False  # Hours filled, should be unavailable
    
    # Check 3: Cutoff time exceeded (original logic)
    # Get the last task in the programming
    last_programming_task = (
        db.query(ProgrammingTask)
        .filter(ProgrammingTask.programming_id == programming.id)
        .order_by(ProgrammingTask.end_time.desc().nullslast())
        .first()
    )
    
    if not last_programming_task or not last_programming_task.end_time:
        return True  # No tasks or no end time, keep available
    
    # Get the team to determine cutoff time
    team = db.query(Team).filter(Team.id == programming.team_id).first()
    if not team:
        return True  # No team found, keep available
    
    # Pass the programming date to handle Saturday logic
    cutoff_time = get_cutoff_time_for_team(team, programming.date)
    max_extension = timedelta(minutes=5)  # Maximum 5 minutes extension
    
    # Create cutoff datetime for the programming date
    cutoff_datetime = datetime.combine(programming.date, cutoff_time)
    max_allowed_time = cutoff_datetime + max_extension
    
    # Check if the last task's end time exceeds the maximum allowed time
    if last_programming_task.end_time > max_allowed_time:
        return False  # Should be unavailable
    
    return True  # Should be available


def update_programming_availability(db: Session, programming: Programming) -> bool:
    """
    Updates the programming status based on date, programmable hours, and cutoff time.
    
    Bidirectional behavior:
    - If all checks pass → Programming becomes "available"
    - If any check fails → Programming becomes "unavailable"
    
    Returns True if the status was changed, False if it remained the same.
    """
    should_be_available = check_programming_availability(db, programming)
    
    if should_be_available and programming.status == ProgrammingStatus.unavailable:
        programming.status = ProgrammingStatus.available
        db.commit()
        return True
    elif not should_be_available and programming.status == ProgrammingStatus.available:
        programming.status = ProgrammingStatus.unavailable
        db.commit()
        return True
    
    return False


def update_programming_availability_by_task(db: Session, task_id: str) -> None:
    """
    Updates the availability of all programmings that contain a specific task.
    This is useful when a task is created, updated, or deleted.
    """
    # Find all programmings that contain this task
    programming_tasks = (
        db.query(ProgrammingTask)
        .filter(ProgrammingTask.task_id == task_id)
        .all()
    )
    
    for pt in programming_tasks:
        programming = db.query(Programming).filter(Programming.id == pt.programming_id).first()
        if programming:
            update_programming_availability(db, programming)


def update_all_programmings_availability_for_date(db: Session, target_date: datetime.date) -> dict:
    """
    Updates the availability of all programmings for a specific date.
    
    Returns a dictionary with the results of the operation.
    """
    programmings = db.query(Programming).filter(Programming.date == target_date).all()
    
    results = {
        "total_programmings": len(programmings),
        "status_changes": 0,
        "available_count": 0,
        "unavailable_count": 0
    }
    
    for programming in programmings:
        status_changed = update_programming_availability(db, programming)
        if status_changed:
            results["status_changes"] += 1
        
        if programming.status == ProgrammingStatus.available:
            results["available_count"] += 1
        else:
            results["unavailable_count"] += 1
    
    return results


def cleanup_past_programmings(db: Session) -> dict:
    """
    Marks all programmings with dates in the past as unavailable.
    This function can be called manually or via a scheduled job.
    
    Returns a dictionary with the results of the operation.
    """
    current_date = date_class.today()
    
    # Query all programmings with past dates that are still marked as available
    past_programmings = (
        db.query(Programming)
        .filter(Programming.date < current_date)
        .filter(Programming.status == ProgrammingStatus.available)
        .all()
    )
    
    results = {
        "total_past_programmings": len(past_programmings),
        "marked_unavailable": 0
    }
    
    for programming in past_programmings:
        programming.status = ProgrammingStatus.unavailable
        results["marked_unavailable"] += 1
    
    if results["marked_unavailable"] > 0:
        db.commit()
    
    return results


def restore_programmings_availability(db: Session) -> dict:
    """
    Revisa todas las programaciones con fecha actual o futura y las marca como 'available'
    si el tiempo programado no excede el límite permitido.
    
    Esta función es útil para "liberar" programaciones que fueron marcadas como 'unavailable'
    pero que ahora tienen espacio disponible (por ejemplo, si se eliminaron tareas).
    
    Returns:
        Diccionario con los resultados de la operación:
        {
            "total_programmings": int,
            "restored_to_available": int,
            "marked_unavailable": int,
            "already_correct": int,
            "details": [...]
        }
    """
    from app.shared.utils.core.logging import get_logger
    logger = get_logger(__name__)
    
    current_date = date_class.today()
    
    # Obtener todas las programaciones con fecha actual o futura
    programmings = (
        db.query(Programming)
        .filter(Programming.date >= current_date)
        .all()
    )
    
    results = {
        "total_programmings": len(programmings),
        "restored_to_available": 0,
        "marked_unavailable": 0,
        "already_correct": 0,
        "details": []
    }
    
    for programming in programmings:
        old_status = programming.status
        should_be_available = check_programming_availability(db, programming)
        
        # Obtener el equipo para logging
        team = db.query(Team).filter(Team.id == programming.team_id).first()
        team_name = team.name if team else "Unknown"
        
        detail = {
            "programming_id": str(programming.id),
            "date": programming.date.isoformat(),
            "team_name": team_name,
            "old_status": old_status.value if hasattr(old_status, 'value') else str(old_status),
            "new_status": None,
            "action": None
        }
        
        if should_be_available and old_status == ProgrammingStatus.unavailable:
            # Restaurar a available
            programming.status = ProgrammingStatus.available
            results["restored_to_available"] += 1
            detail["new_status"] = "available"
            detail["action"] = "restored"
            logger.info(f"Restored programming {programming.id} ({team_name}, {programming.date}) to available")
            
        elif not should_be_available and old_status == ProgrammingStatus.available:
            # Marcar como unavailable
            programming.status = ProgrammingStatus.unavailable
            results["marked_unavailable"] += 1
            detail["new_status"] = "unavailable"
            detail["action"] = "marked_unavailable"
            logger.info(f"Marked programming {programming.id} ({team_name}, {programming.date}) as unavailable")
            
        else:
            # Ya tiene el estado correcto
            results["already_correct"] += 1
            detail["new_status"] = old_status.value if hasattr(old_status, 'value') else str(old_status)
            detail["action"] = "no_change"
        
        results["details"].append(detail)
    
    # Commit todos los cambios
    if results["restored_to_available"] > 0 or results["marked_unavailable"] > 0:
        db.commit()
        logger.info(f"Restored {results['restored_to_available']} programmings to available, "
                   f"marked {results['marked_unavailable']} as unavailable")
    
    return results



def get_programming_availability(db: Session, programming_id: str, task_duration: float) -> dict:
    """
    Calcula el tiempo ya ocupado en una programación específica y determina si hay suficiente tiempo disponible para una nueva tarea.
    
    Args:
        db: Sesión de base de datos
        programming_id: ID de la programación
        task_duration: Duración de la tarea en minutos
        
    Returns:
        Diccionario con detalles de disponibilidad:
        {
            "available": bool,
            "current_end_minutes": int,
            "final_minutes": int,
            "max_allowed_minutes": float,
            "team_name": str
        }
    """
    from app.modules.programming.services.utils.programming_utils import ProgrammingUtils
    from app.shared.utils.core.logging import get_logger
    
    logger = get_logger(__name__)
    
    # Obtener la programación
    programming = db.query(Programming).filter(Programming.id == programming_id).first()
    if not programming:
        logger.error(f"Programming {programming_id} not found")
        return {
            "available": False,
            "error": "Programming not found"
        }
        
    # Obtener el equipo
    team = db.query(Team).filter(Team.id == programming.team_id).first()
    team_name = team.name if team else "Unknown"
    
    # Determinar duración máxima permitida
    team_rule = get_team_rule(team_name)
    if team_rule and "duration" in team_rule:
        duration_minutes = team_rule["duration"]
    else:
        duration_minutes = STANDARD_DURATION_MINUTES
        
    # Aplicar tolerancia (por defecto 10 minutos, hardcoded por ahora para coincidir con lógica anterior)
    tolerance_minutes = 10
    STANDARD_START_MINUTES = 420  # 7:00 AM
    
    if duration_minutes is None:
        max_allowed_minutes = float('inf')
    else:
        # Sumar hora de inicio (420) + duración (460) + tolerancia (10) = 890 (14:50)
        max_allowed_minutes = STANDARD_START_MINUTES + duration_minutes + tolerance_minutes
        
    # Calcular tiempo ocupado actual
    programming_tasks = db.query(ProgrammingTask).filter(
        ProgrammingTask.programming_id == programming_id
    ).all()
    
    current_end_minutes = ProgrammingUtils.calculate_current_programming_time(
        programming_tasks, programming.date
    )
    
    # Calcular tiempo final
    final_minutes = current_end_minutes + task_duration
    
    # Determinar disponibilidad
    is_available = final_minutes <= max_allowed_minutes

    logger.info(f"Availability Check: Team='{team_name}', Rule={team_rule}, Duration={duration_minutes}, "
                f"MaxAllowed={max_allowed_minutes}, Current={current_end_minutes}, "
                f"Task={task_duration}, Final={final_minutes}, Available={is_available}")
    
    return {
        "available": is_available,
        "current_end_minutes": current_end_minutes,
        "final_minutes": final_minutes,
        "max_allowed_minutes": max_allowed_minutes,
        "team_name": team_name
    }
