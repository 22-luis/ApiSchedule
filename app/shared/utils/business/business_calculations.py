"""
Servicio para cálculos de negocio centralizados.
Contiene fórmulas y reglas de cálculo que se utilizan en toda la aplicación.
"""
import math
from datetime import date, datetime, time, timedelta
from typing import Dict, Any, List, Optional
from app.modules.programming.schemas.calculations import (
    TaskDurationRequest, 
    TaskDurationResponse, 
    WorkingHoursResponse
)

class BusinessCalculations:
    
    @staticmethod
    def calculate_task_minutes(quantity: float, productivity: float, people: float, code_people: Optional[float] = None) -> int:
        """
        Calcula los minutos planeados para una tarea.
        Fórmula: (Cantidad * (1/Productividad) * 60) * (Personas Requeridas / Personas Asignadas)
        """
        # Validaciones
        if not quantity or quantity <= 0:
            return 0
        if not productivity or productivity <= 0:
            return 0
        if not people or people < 1:
            return 0
            
        base_minutes = (quantity * (1 / productivity) * 60)

        # Si hay personas requeridas por código, aplicar factor de ajuste
        if code_people is not None and people > 0 and code_people > 0:
            minutes = base_minutes * (code_people / people)
        else:
            minutes = base_minutes

        return math.ceil(minutes)
    
    @staticmethod
    def calculate_task_duration(request: TaskDurationRequest) -> TaskDurationResponse:
        """Calcula la duración de una tarea basándose en el request."""
        minutes = BusinessCalculations.calculate_task_minutes(
            request.quantity,
            request.productivity,
            request.people,
            request.code_people
        )
        
        hours = minutes / 60.0

        base_formula = f"({request.quantity} / {request.productivity} * 60)"
        
        if request.code_people is not None and request.people > 0 and request.code_people > 0:
            formula_used = f"{base_formula} * ({request.code_people} / {request.people}) = {minutes} minutos"
        else:
            formula_used = f"{base_formula} = {minutes} minutos"

        return TaskDurationResponse(
            minutes=minutes,
            hours=round(hours, 2),
            formula_used=formula_used
        )
    
    @staticmethod
    def get_working_hours(target_date: date) -> WorkingHoursResponse:
        """Retorna las horas de trabajo configuradas para una fecha específica."""
        weekday = target_date.weekday()  # 0=Lunes, 6=Domingo
        
        if weekday == 5:  # Sábado
            start_hour = 7
            start_minute = 30
            end_hour = 11
            end_minute = 30
            is_working_day = True
        elif weekday == 6:  # Domingo
            start_hour = 0
            start_minute = 0
            end_hour = 0
            end_minute = 0
            is_working_day = False
        else:  # Lunes a Viernes
            start_hour = 7
            start_minute = 0
            end_hour = 16
            end_minute = 0
            is_working_day = True
        
        # Calcular total de horas
        total_hours = 0.0
        if is_working_day:
            total_hours = (end_hour - start_hour) + (end_minute - start_minute) / 60.0
        
        return WorkingHoursResponse(
            start_hour=start_hour,
            start_minute=start_minute,
            end_hour=end_hour,
            end_minute=end_minute,
            is_working_day=is_working_day,
            total_hours=round(total_hours, 2)
        )
    
    @staticmethod
    def calculate_programming_base_time(target_date: date) -> Optional[datetime]:
        """Calcula el datetime de inicio de programación para un día."""
        working_hours = BusinessCalculations.get_working_hours(target_date)
        
        if not working_hours.is_working_day:
            return None
        
        return datetime.combine(
            target_date,
            time(working_hours.start_hour, working_hours.start_minute)
        )
    
    @staticmethod
    def calculate_sequential_times(
        base_date: date,
        tasks: list,
        base_time: Optional[str] = None
    ) -> list:
        """Calcula tiempos de inicio y fin para una lista de tareas secuenciales."""
        # Obtener hora base
        if base_time:
            hour, minute = map(int, base_time.split(":"))
            current_time = datetime.combine(base_date, time(hour, minute))
        else:
            current_time = BusinessCalculations.calculate_programming_base_time(base_date)
            if not current_time:
                return []
        
        result = []
        for i, task in enumerate(tasks):
            if isinstance(task, dict):
                minutes = task.get('minutes', 0) or 0
                task_id = task.get('id')
                description = task.get('description', '')
            else:
                minutes = getattr(task, 'minutes', 0) or 0
                task_id = getattr(task, 'id', None)
                description = getattr(task, 'description', '')
            
            start_time = current_time
            end_time = current_time + timedelta(minutes=minutes)
            
            result.append({
                'id': task_id,
                'description': description,
                'minutes': minutes,
                'start_time': start_time.isoformat(),
                'end_time': end_time.isoformat()
            })
            
            current_time = end_time
        
        return result
    
    @staticmethod
    def calculate_task_efficiency(planned_minutes: int, actual_minutes: int) -> Dict[str, Any]:
        """Calcula la eficiencia de una tarea completada."""
        if planned_minutes <= 0:
            return {
                'efficiency_percentage': 0,
                'time_difference': 0,
                'status': 'invalid_planned_time'
            }
        
        efficiency = (planned_minutes / actual_minutes) * 100 if actual_minutes > 0 else 0
        time_diff = actual_minutes - planned_minutes
        
        if efficiency >= 95:
            status = 'excellent'
        elif efficiency >= 85:
            status = 'good'
        elif efficiency >= 70:
            status = 'acceptable'
        else:
            status = 'needs_improvement'
        
        return {
            'efficiency_percentage': round(efficiency, 2),
            'time_difference': time_diff,
            'status': status,
            'planned_minutes': planned_minutes,
            'actual_minutes': actual_minutes
        }
    
    @staticmethod
    def calculate_team_workload(tasks: List[Dict[str, Any]], working_hours: int = 8) -> Dict[str, Any]:
        """Calcula la carga de trabajo total para un equipo en base a sus tareas."""
        total_minutes = sum(task.get('minutes', 0) for task in tasks)
        total_hours = total_minutes / 60
        
        workload_percentage = (total_hours / working_hours) * 100
        
        if workload_percentage <= 70:
            level = 'light'
        elif workload_percentage <= 90:
            level = 'moderate'
        elif workload_percentage <= 110:
            level = 'high'
        else:
            level = 'overloaded'
        
        return {
            'total_minutes': total_minutes,
            'total_hours': round(total_hours, 2),
            'workload_percentage': round(workload_percentage, 2),
            'level': level,
            'working_hours': working_hours,
            'task_count': len(tasks)
        }
