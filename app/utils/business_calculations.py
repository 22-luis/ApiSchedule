"""
Servicio para cálculos de negocio centralizados.
Contiene fórmulas y reglas de cálculo que se utilizan en toda la aplicación.
"""
import math
from typing import Optional, Dict, Any
from datetime import datetime, date, time
from pydantic import BaseModel


class TaskDurationRequest(BaseModel):
    """Esquema para solicitud de cálculo de duración de tarea"""
    quantity: int
    productivity: float
    people: int


class TaskDurationResponse(BaseModel):
    """Esquema para respuesta de cálculo de duración de tarea"""
    minutes: int
    hours: float
    formula_used: str


class WorkingHoursRequest(BaseModel):
    """Esquema para solicitud de horas de trabajo"""
    date: date


class WorkingHoursResponse(BaseModel):
    """Esquema para respuesta de horas de trabajo"""
    start_hour: int
    start_minute: int
    end_hour: int
    end_minute: int
    is_working_day: bool
    total_hours: float


class BusinessCalculations:
    """Servicio centralizado para cálculos de negocio"""
    
    @staticmethod
    def calculate_task_minutes(quantity: int, productivity: float, people: int) -> int:
        """
        Calcula los minutos de una tarea basado en la fórmula de negocio:
        minutos = (cantidad * productividad * 60) / personas
        
        Args:
            quantity: Cantidad a producir
            productivity: Productividad (tiempo por unidad)
            people: Número de personas asignadas
            
        Returns:
            int: Minutos calculados (redondeado hacia arriba)
        """
        # Validaciones
        if not quantity or quantity <= 0:
            return 0
        if not productivity or productivity <= 0:
            return 0
        if not people or people < 1:
            return 0
            
        # Fórmula de negocio: (cantidad * productividad * 60) / personas
        minutes = (quantity * productivity * 60) / people
        
        # Redondear hacia arriba (ceiling)
        return math.ceil(minutes)
    
    @staticmethod
    def calculate_task_duration(request: TaskDurationRequest) -> TaskDurationResponse:
        """
        Calcula la duración de una tarea con información detallada.
        
        Args:
            request: Solicitud con cantidad, productividad y personas
            
        Returns:
            TaskDurationResponse: Respuesta con minutos, horas y fórmula utilizada
        """
        minutes = BusinessCalculations.calculate_task_minutes(
            request.quantity,
            request.productivity,
            request.people
        )
        
        hours = minutes / 60.0
        
        return TaskDurationResponse(
            minutes=minutes,
            hours=round(hours, 2),
            formula_used=f"({request.quantity} × {request.productivity} × 60) ÷ {request.people} = {minutes} minutos"
        )
    
    @staticmethod
    def get_working_hours(target_date: date) -> WorkingHoursResponse:
        """
        Obtiene las horas de trabajo para una fecha específica.
        
        Args:
            target_date: Fecha para la cual obtener las horas de trabajo
            
        Returns:
            WorkingHoursResponse: Horas de trabajo configuradas
        """
        weekday = target_date.weekday()  # 0=Lunes, 6=Domingo
        
        # Configuración de horas de trabajo
        if weekday == 5:  # Sábado
            start_hour = 7
            start_minute = 30
            end_hour = 17
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
            end_hour = 17
            end_minute = 0
            is_working_day = True
        
        # Calcular total de horas
        if is_working_day:
            total_hours = (end_hour - start_hour) + (end_minute - start_minute) / 60.0
        else:
            total_hours = 0.0
        
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
        """
        Calcula la hora base de programación para una fecha específica.
        
        Args:
            target_date: Fecha para la cual calcular la hora base
            
        Returns:
            datetime: Hora base de programación o None si no es día laboral
        """
        working_hours = BusinessCalculations.get_working_hours(target_date)
        
        if not working_hours.is_working_day:
            return None
        
        # Crear datetime con la hora base
        base_time = datetime.combine(
            target_date,
            time(working_hours.start_hour, working_hours.start_minute)
        )
        
        return base_time
    
    @staticmethod
    def calculate_sequential_times(
        base_date: date,
        tasks: list,
        base_time: Optional[str] = None
    ) -> list:
        """
        Calcula tiempos secuenciales para una lista de tareas.
        
        Args:
            base_date: Fecha base de programación
            tasks: Lista de tareas con campo 'minutes'
            base_time: Hora base opcional (formato "HH:MM")
            
        Returns:
            list: Lista de tareas con start_time y end_time calculados
        """
        print(f"[DEBUG] calculate_sequential_times called with:")
        print(f"  base_date: {base_date}")
        print(f"  tasks: {tasks}")
        print(f"  base_time: {base_time}")
        
        # Obtener hora base
        if base_time:
            hour, minute = map(int, base_time.split(":"))
            current_time = datetime.combine(base_date, time(hour, minute))
        else:
            current_time = BusinessCalculations.calculate_programming_base_time(base_date)
            if not current_time:
                print("[DEBUG] No base time calculated, returning empty list")
                return []
        
        print(f"[DEBUG] Starting time: {current_time}")
        
        result = []
        
        for i, task in enumerate(tasks):
            # Extraer minutes del diccionario o objeto
            if isinstance(task, dict):
                minutes = task.get('minutes', 0) or 0
                task_id = task.get('id')
                description = task.get('description', '')
            else:
                minutes = getattr(task, 'minutes', 0) or 0
                task_id = getattr(task, 'id', None)
                description = getattr(task, 'description', '')
            
            print(f"[DEBUG] Task {i}: {description}, minutes: {minutes}")
            
            # Calcular tiempos
            start_time = current_time
            
            # Calcular end_time correctamente manejando horas y minutos
            total_minutes = current_time.hour * 60 + current_time.minute + minutes
            end_hour = total_minutes // 60
            end_minute = total_minutes % 60
            end_time = current_time.replace(hour=end_hour, minute=end_minute)
            
            print(f"[DEBUG] Task {i} times: {start_time} -> {end_time}")
            
            # Agregar a resultado
            task_with_times = {
                'id': task_id,
                'description': description,
                'minutes': minutes,
                'start_time': start_time.isoformat(),
                'end_time': end_time.isoformat()
            }
            result.append(task_with_times)
            
            # Actualizar tiempo actual para la siguiente tarea
            current_time = end_time
        
        print(f"[DEBUG] Final result: {result}")
        return result
    
    @staticmethod
    def validate_task_parameters(quantity: int, productivity: float, people: int) -> Dict[str, Any]:
        """
        Valida los parámetros de una tarea y retorna errores si los hay.
        
        Args:
            quantity: Cantidad a producir
            productivity: Productividad
            people: Número de personas
            
        Returns:
            Dict: Diccionario con validación y errores
        """
        errors = []
        
        if not quantity or quantity <= 0:
            errors.append("La cantidad debe ser mayor a 0")
        
        if not productivity or productivity <= 0:
            errors.append("La productividad debe ser mayor a 0")
        
        if not people or people < 1:
            errors.append("El número de personas debe ser mayor a 0")
        
        return {
            'is_valid': len(errors) == 0,
            'errors': errors,
            'warnings': []
        }
