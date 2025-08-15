"""
Servicio para cálculos de negocio centralizados.
Contiene fórmulas y reglas de cálculo que se utilizan en toda la aplicación.
"""
import math
from datetime import date, datetime, time
from typing import Dict, Any, List, Optional
from pydantic import BaseModel
import pytz


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


class TimeZoneUtils:
    """Utilidades para manejo de zonas horarias"""
    
    @staticmethod
    def get_el_salvador_timezone():
        """Obtiene la zona horaria de El Salvador"""
        return pytz.timezone('America/El_Salvador')
    
    @staticmethod
    def convert_to_el_salvador_time(utc_datetime: datetime) -> datetime:
        """Convierte una fecha UTC a hora de El Salvador"""
        if utc_datetime.tzinfo is None:
            utc_datetime = pytz.UTC.localize(utc_datetime)
        return utc_datetime.astimezone(TimeZoneUtils.get_el_salvador_timezone())
    
    @staticmethod
    def format_time_el_salvador(time_str: str) -> str:
        """Formatea una hora para mostrar en la zona horaria de El Salvador"""
        if not time_str:
            return '-'
        
        try:
            # Si es formato HH:mm, devolver directamente
            if ':' in time_str and 'T' not in time_str:
                time_parts = time_str.split(':')
                if len(time_parts) >= 2:
                    hour = int(time_parts[0])
                    minute = time_parts[1]
                    ampm = 'p. m.' if hour >= 12 else 'a. m.'
                    display_hour = 12 if hour == 0 else hour - 12 if hour > 12 else hour
                    return f"{display_hour}:{minute} {ampm}"
            
            # Para formato ISO
            date_obj = datetime.fromisoformat(time_str.replace('Z', '+00:00'))
            el_salvador_time = TimeZoneUtils.convert_to_el_salvador_time(date_obj)
            
            hours = el_salvador_time.hour
            minutes = el_salvador_time.minute
            seconds = el_salvador_time.second
            
            ampm = 'p. m.' if hours >= 12 else 'a. m.'
            display_hour = 12 if hours == 0 else hours - 12 if hours > 12 else hours
            
            return f"{display_hour}:{minutes:02d}:{seconds:02d} {ampm}"
            
        except Exception as e:
            print(f"Error formateando hora El Salvador: {e}")
            return '-'
    
    @staticmethod
    def get_programming_base_time_utc(target_date: date) -> Optional[datetime]:
        """Calcula la hora base de programación en UTC para una fecha"""
        try:
            # Determinar hora base según el día
            day_of_week = target_date.weekday()  # 0=Lunes, 6=Domingo
            
            if day_of_week == 6:  # Domingo
                return None
            
            # Configurar hora base
            if day_of_week == 5:  # Sábado
                base_hour = 7
                base_minute = 30
            else:  # Lunes a Viernes
                base_hour = 7
                base_minute = 0
            
            # Crear datetime en zona horaria de El Salvador
            el_salvador_tz = TimeZoneUtils.get_el_salvador_timezone()
            local_datetime = el_salvador_tz.localize(
                datetime.combine(target_date, time(base_hour, base_minute))
            )
            
            # Convertir a UTC
            utc_datetime = local_datetime.astimezone(pytz.UTC)
            return utc_datetime
            
        except Exception as e:
            print(f"Error calculando hora base UTC: {e}")
            return None

class BusinessCalculations:
    """Servicio centralizado para cálculos de negocio"""
    
    @staticmethod
    def calculate_task_minutes(quantity: float, productivity: float, people: float) -> int:
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
    def validate_task_parameters(quantity: float, productivity: float, people: float) -> Dict[str, Any]:
        """
        Valida los parámetros de una tarea y retorna errores si los hay.
        
        Args:
            quantity: Cantidad a producir
            productivity: Productividad
            people: Número de personas
            
        Returns:
            Dict: Diccionario con validación y errores
        """
        print(f"[DEBUG] validate_task_parameters - Validando: quantity={quantity}, productivity={productivity}, people={people}")
        
        errors = []
        
        if not quantity or quantity <= 0:
            errors.append("La cantidad debe ser mayor a 0")
            print(f"[DEBUG] Error: cantidad={quantity} no es válida")
        
        if not productivity or productivity <= 0:
            errors.append("La productividad debe ser mayor a 0")
            print(f"[DEBUG] Error: productividad={productivity} no es válida")
        
        if not people or people < 1:
            errors.append("El número de personas debe ser mayor a 0")
            print(f"[DEBUG] Error: people={people} no es válida")
        
        print(f"[DEBUG] validate_task_parameters - Errores encontrados: {errors}")
        
        return {
            'is_valid': len(errors) == 0,
            'errors': errors,
            'warnings': []
        }
    
    @staticmethod
    def validate_task_form_data(form_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Valida los datos completos de un formulario de tarea.
        
        Args:
            form_data: Diccionario con todos los campos del formulario
            
        Returns:
            Dict: Resultado de validación con errores y advertencias
        """
        errors = []
        warnings = []
        
        # Validaciones obligatorias
        if not form_data.get('code'):
            errors.append('El código es obligatorio')
        
        if not form_data.get('activity'):
            errors.append('La actividad es obligatoria')
        
        # Validaciones de cantidad y personas (solo si no hay código válido)
        if not form_data.get('code_id'):
            if not form_data.get('quantity') or float(form_data.get('quantity', 0)) <= 0:
                errors.append('La cantidad debe ser mayor a 0')
            
            if not form_data.get('people') or int(form_data.get('people', 0)) <= 0:
                errors.append('El número de personas debe ser mayor a 0')
        
        # Validaciones de equipo y programación
        if not form_data.get('selectedTeam'):
            errors.append('Debe seleccionar un equipo')
        
        if not form_data.get('programmingId'):
            errors.append('No hay programación activa')
        
        # Validaciones de productividad
        if form_data.get('productivity'):
            try:
                productivity = float(form_data['productivity'])
                if productivity <= 0:
                    errors.append('La productividad debe ser mayor a 0')
                elif productivity > 24:
                    warnings.append('La productividad parece muy alta (>24 horas por unidad)')
            except ValueError:
                errors.append('La productividad debe ser un número válido')
        
        # Validaciones de lote
        if form_data.get('lote'):
            lote = str(form_data['lote']).strip()
            if lote and lote != '-':
                try:
                    int(lote)
                except ValueError:
                    errors.append('El lote debe ser un número válido')
        
        return {
            'is_valid': len(errors) == 0,
            'errors': errors,
            'warnings': warnings
        }
    
    @staticmethod
    def validate_extra_task_data(description: str, minutes: str, selected_team: str, programming_id: str) -> Dict[str, Any]:
        """
        Valida los datos de una tarea extra.
        
        Args:
            description: Descripción de la tarea
            minutes: Minutos de duración
            selected_team: Equipo seleccionado
            programming_id: ID de programación
            
        Returns:
            Dict: Resultado de validación
        """
        errors = []
        
        if not description or not description.strip():
            errors.append('La descripción es obligatoria')
        
        if not minutes or float(minutes) <= 0:
            errors.append('Los minutos deben ser mayor a 0')
        
        if not selected_team:
            errors.append('Debe seleccionar un equipo')
        
        if not programming_id:
            errors.append('No hay programación activa')
        
        return {
            'is_valid': len(errors) == 0,
            'errors': errors,
            'warnings': []
        }
    
    @staticmethod
    def calculate_task_efficiency(planned_minutes: int, actual_minutes: int) -> Dict[str, Any]:
        """
        Calcula la eficiencia de una tarea comparando tiempo planificado vs real.
        
        Args:
            planned_minutes: Minutos planificados
            actual_minutes: Minutos reales
            
        Returns:
            Dict: Métricas de eficiencia
        """
        if planned_minutes <= 0:
            return {
                'efficiency_percentage': 0,
                'time_difference': 0,
                'status': 'invalid_planned_time'
            }
        
        efficiency = (planned_minutes / actual_minutes) * 100 if actual_minutes > 0 else 0
        time_diff = actual_minutes - planned_minutes
        
        # Determinar status
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
        """
        Calcula la carga de trabajo de un equipo.
        
        Args:
            tasks: Lista de tareas del equipo
            working_hours: Horas de trabajo por día
            
        Returns:
            Dict: Métricas de carga de trabajo
        """
        total_minutes = sum(task.get('minutes', 0) for task in tasks)
        total_hours = total_minutes / 60
        
        workload_percentage = (total_hours / working_hours) * 100
        
        # Determinar nivel de carga
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
