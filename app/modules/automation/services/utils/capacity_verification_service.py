from typing import Dict, Any, List, cast
from sqlalchemy.orm import Session
from datetime import date
from app.modules.programming.models.programming import Programming, ProgrammingTask
from app.modules.programming.models.task import Task

class CapacityVerificationService:
    """
    Servicio para verificar la capacidad de programación de equipos.
    
    Capacidades estándar:
    - Lunes a Viernes: 460 minutos (7:00 AM - 2:40 PM)
    - Sábados: 220 minutos (7:30 AM - 11:10 AM)
    - Domingos: No hay programación
    
    Margen de error: ±5 minutos
    """
    
    # Constantes de configuración
    WEEKDAY_MINUTES = 460      # Lunes a Viernes
    SATURDAY_MINUTES = 220     # Sábados
    TOLERANCE_MINUTES = 5      # Margen de error
    
    @staticmethod
    def get_daily_capacity(programming_date: date) -> Dict[str, int]:
        """
        Obtiene la capacidad diaria según el día de la semana.
        
        Args:
            programming_date: Fecha de la programación
            
        Returns:
            Diccionario con capacidades:
            {
                "max_minutes": int,      # Capacidad máxima del día
                "min_capacity": int,     # Límite inferior (max - tolerancia)
                "max_capacity": int      # Límite superior (max + tolerancia)
            }
        """
        # weekday() retorna: 0=Lunes, 1=Martes, ..., 5=Sábado, 6=Domingo
        day_of_week = programming_date.weekday()
        
        if day_of_week == 6:  # Domingo
            # No hay programación los domingos
            max_minutes = 0
        elif day_of_week == 5:  # Sábado
            max_minutes = CapacityVerificationService.SATURDAY_MINUTES
        else:  # Lunes a Viernes (0-4)
            max_minutes = CapacityVerificationService.WEEKDAY_MINUTES
        
        return {
            "max_minutes": max_minutes,
            "min_capacity": max_minutes - CapacityVerificationService.TOLERANCE_MINUTES,
            "max_capacity": max_minutes + CapacityVerificationService.TOLERANCE_MINUTES
        }
    
    @staticmethod
    def check_team_capacity(db: Session, team_id: str, programming_date: date) -> Dict[str, Any]:
        """
        Verifica si un equipo ha llegado a su límite de capacidad para una fecha específica.
        
        Args:
            db: Sesión de base de datos
            team_id: ID del equipo a verificar
            programming_date: Fecha de la programación
            
        Returns:
            Diccionario con información de capacidad:
            {
                "has_capacity": bool,        # True si aún tiene capacidad
                "total_minutes": int,        # Total de minutos programados
                "remaining_minutes": int,    # Minutos restantes
                "is_at_limit": bool,         # True si está en el rango límite
                "is_over_limit": bool,       # True si superó el límite
                "percentage_used": float,    # Porcentaje de capacidad utilizada
                "max_daily_minutes": int,    # Capacidad máxima del día
                "day_type": str              # "weekday", "saturday", o "sunday"
            }
        """
        # Obtener la capacidad del día
        daily_capacity = CapacityVerificationService.get_daily_capacity(programming_date)
        max_minutes = daily_capacity["max_minutes"]
        min_capacity = daily_capacity["min_capacity"]
        max_capacity = daily_capacity["max_capacity"]
        
        # Determinar tipo de día
        day_of_week = programming_date.weekday()
        if day_of_week == 6:
            day_type = "sunday"
        elif day_of_week == 5:
            day_type = "saturday"
        else:
            day_type = "weekday"
        
        # Buscar la programación del equipo para la fecha especificada
        programming = db.query(Programming).filter(
            Programming.team_id == team_id,
            Programming.date == programming_date
        ).first()
        
        if not programming:
            # No hay programación para este equipo en esta fecha
            return {
                "has_capacity": True,
                "total_minutes": 0,
                "remaining_minutes": max_minutes,
                "is_at_limit": False,
                "is_over_limit": False,
                "percentage_used": 0.0,
                "max_daily_minutes": max_minutes,
                "day_type": day_type
            }
        
        # Calcular el total de minutos de todas las tareas en la programación
        total_minutes = 0
        programming_tasks = cast(List[ProgrammingTask], cast(Any, db.query(ProgrammingTask).filter(
            ProgrammingTask.programming_id == programming.id
        ).all()))
        
        for prog_task in programming_tasks:
            task = db.query(Task).filter(Task.id == prog_task.task_id).first()
            if task and task.minutes:
                total_minutes += task.minutes
        
        # Calcular métricas
        remaining_minutes = max_minutes - total_minutes
        is_at_limit = (min_capacity <= total_minutes <= max_capacity) if max_minutes > 0 else False
        is_over_limit = total_minutes > max_capacity if max_minutes > 0 else False
        has_capacity = total_minutes < min_capacity if max_minutes > 0 else False
        percentage_used = (total_minutes / max_minutes * 100) if max_minutes > 0 else 0.0
        
        return {
            "has_capacity": has_capacity,
            "total_minutes": total_minutes,
            "remaining_minutes": remaining_minutes,
            "is_at_limit": is_at_limit,
            "is_over_limit": is_over_limit,
            "percentage_used": round(percentage_used, 2),
            "max_daily_minutes": max_minutes,
            "day_type": day_type
        }
    
    @staticmethod
    def get_available_minutes(db: Session, team_id: str, programming_date: date) -> int:
        """
        Obtiene los minutos disponibles para un equipo en una fecha específica.
        
        Args:
            db: Sesión de base de datos
            team_id: ID del equipo
            programming_date: Fecha de la programación
            
        Returns:
            Minutos disponibles (puede ser negativo si está sobre el límite)
        """
        capacity_info = CapacityVerificationService.check_team_capacity(db, team_id, programming_date)
        return capacity_info["remaining_minutes"]
    
    @staticmethod
    def can_add_task(db: Session, team_id: str, programming_date: date, task_minutes: int) -> Dict[str, Any]:
        """
        Verifica si se puede agregar una tarea a la programación de un equipo.
        
        Args:
            db: Sesión de base de datos
            team_id: ID del equipo
            programming_date: Fecha de la programación
            task_minutes: Minutos de la tarea a agregar
            
        Returns:
            Diccionario con información:
            {
                "can_add": bool,              # True si se puede agregar la tarea
                "current_minutes": int,       # Minutos actuales
                "new_total": int,             # Total si se agrega la tarea
                "would_exceed_limit": bool,   # True si excedería el límite
                "message": str,               # Mensaje descriptivo
                "max_daily_minutes": int,     # Capacidad máxima del día
                "day_type": str               # Tipo de día
            }
        """
        capacity_info = CapacityVerificationService.check_team_capacity(db, team_id, programming_date)
        current_minutes = capacity_info["total_minutes"]
        max_daily_minutes = capacity_info["max_daily_minutes"]
        day_type = capacity_info["day_type"]
        
        # Obtener límite superior
        daily_capacity = CapacityVerificationService.get_daily_capacity(programming_date)
        max_capacity = daily_capacity["max_capacity"]
        
        new_total = current_minutes + task_minutes
        would_exceed_limit = new_total > max_capacity
        
        can_add = not would_exceed_limit
        
        if can_add:
            message = f"Se puede agregar la tarea. Total resultante: {new_total}/{max_daily_minutes} minutos ({day_type})."
        else:
            message = f"No se puede agregar la tarea. Excedería el límite: {new_total}/{max_daily_minutes} minutos ({day_type})."
        
        return {
            "can_add": can_add,
            "current_minutes": current_minutes,
            "new_total": new_total,
            "would_exceed_limit": would_exceed_limit,
            "message": message,
            "max_daily_minutes": max_daily_minutes,
            "day_type": day_type
        }
