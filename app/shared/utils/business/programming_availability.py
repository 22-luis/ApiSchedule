from datetime import datetime, time, timedelta, date as date_class
from sqlalchemy.orm import Session
from app.modules.programming.models.programming import Programming, ProgrammingTask
from app.modules.core.models.team import Team
from app.modules.programming.models.state import ProgrammingStatus
from typing import Optional


def get_team_type(team: Team) -> str:
    name = (team.name or '').lower()
    if "fabricado" in name:
        return "fabricado"
    if "molino" in name:
        return "molino"
    if "pesado" in name:
        return "pesado"
    return "otro"


def get_cutoff_time_for_team(team: Team, date_obj: datetime.date = None) -> time:
    # If date is provided and it's Saturday (weekday 5), return 12:30
    if date_obj and date_obj.weekday() == 5:
        return time(12, 30)
        
    team_type = get_team_type(team)
    team_name = (team.name or '').lower()
    
    if "fabricado 3" in team_name:
        return time(15, 40)
    elif team_type == "pesado":
        return time(14, 40)  # Pesado now follows standard time (was 17:40)
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
        "duration": STANDARD_DURATION_MINUTES
    },
    "Fabricado 1": {
        "duration": STANDARD_DURATION_MINUTES
    },
    "Fabricado 2": {
        "duration": STANDARD_DURATION_MINUTES
    },
    "Fabricado 3": {
        "duration": 520  # 7:00 AM to 15:40 PM = 520 minutes
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
            STANDARD_START_MINUTES = 420  # 7:00 AM
            
            # Determinar hora de inicio y duración según el día de la semana
            is_saturday = programming.date.weekday() == 5
            
            if is_saturday:
                # Para sábados: 7:30 AM - 12:30 PM
                saturday_start = 450  # 7:30 AM
                day_duration = 300  # 12:30 PM - 7:30 AM = 300 minutos
                max_allowed_minutes = saturday_start + day_duration + tolerance_minutes
            else:
                # Para días de semana
                if duration_minutes is None:
                    max_allowed_minutes = float('inf')
                else:
                    # Sumar hora de inicio (420) + duración (460) + tolerancia (10) = 890 (14:50)
                    max_allowed_minutes = STANDARD_START_MINUTES + duration_minutes + tolerance_minutes
                
                # Calculate current total time using the utility function
                from app.modules.automation.services.utils.programming_utils import ProgrammingUtils
                current_end_minutes = ProgrammingUtils.calculate_current_programming_time(
                    programming_tasks, programming.date
                )
                
                # Check if programmable hours are filled
                if current_end_minutes >= max_allowed_minutes:
                    # Log for debugging
                    from app.shared.utils.core.logging import get_logger
                    logger = get_logger("availability")
                    logger.debug(f"Capacidad agotada para {team_name} el {programming.date}: {current_end_minutes} >= {max_allowed_minutes}")
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
    
    # Localizar el tiempo de la tarea si es necesario
    from pytz import timezone
    sv_tz = timezone("America/El_Salvador")
    
    task_end_time = last_programming_task.end_time
    if task_end_time.tzinfo is not None:
        # Si ya tiene zona horaria, convertimos a local
        task_end_time = task_end_time.astimezone(sv_tz).replace(tzinfo=None)
    # Si es naive, asumimos que ya es local

    # Check if the last task's end time exceeds the maximum allowed time
    if task_end_time > max_allowed_time:
        return False  # Should be unavailable
    
    return True  # Should be available


def update_programming_availability(db: Session, programming: Programming) -> bool:
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
    from app.modules.automation.services.utils.programming_utils import ProgrammingUtils
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
    
    # BLOQUEO EXPLÍCITO DE DOMINGOS: Los domingos NO se programan NUNCA
    if programming.date.weekday() == 6:
        logger.info(f"Programming {programming_id} rejected: Sunday (no programming allowed)")
        return {
            "available": False,
            "current_end_minutes": 0,
            "final_minutes": 0,
            "max_allowed_minutes": 0,
            "team_name": "N/A",
            "reason": "Sundays are not allowed for programming"
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
    
    # Determinar hora de inicio y duración según el día de la semana
    is_saturday = programming.date.weekday() == 5
    
    if is_saturday:
        STANDARD_START_MINUTES = 450  # 7:30 AM
        # Para sábados, la duración es fija hasta las 12:30 (750 min)
        # 12:30 = 750 minutos. Duración = 750 - 450 = 300 minutos
        day_duration = 300
        max_allowed_minutes = STANDARD_START_MINUTES + day_duration + tolerance_minutes
    else:
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

    try:
        with open("scheduling_debug.log", "a") as f:
            f.write(f"[{datetime.now()}] Team={team_name}, Date={programming.date}, CurrentEnd={current_end_minutes}, Task={task_duration}, Final={final_minutes}, Max={max_allowed_minutes}, Available={is_available}\n")
    except:
        pass

    if not is_available:
        logger.warning(f"REJECTED: Team='{team_name}', Date={programming.date}, Final={final_minutes} > MaxAllowed={max_allowed_minutes}. (Current: {current_end_minutes}, Task: {task_duration})")
    else:
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
