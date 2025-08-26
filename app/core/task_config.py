from typing import List, Dict, Any
from pydantic import BaseModel, Field
from datetime import time
from enum import Enum
from sqlalchemy.orm import Session
from app.models.team import Team
from app.models.programming import Programming, ProgrammingStatus

class WeighingTeams(str, Enum):
    Pesado = "Pesado"
    
class WeighingActivities(str, Enum):
    Pesado = "PESADO"
    
class ManufacturingTeams(str, Enum):
    Fabricado1 = "Fabricado 1"
    Fabricado2 = "Fabricado 2"
    Fabricado3 = "Fabricado 3"
    Molino = "Molino"
    
class ManufacturingActivities(str, Enum):
    Mol_pasta = "MOLIENDA EN PASTA"
    Mol_polvo = "MOLIENDA EN POLVO"
    Mez_polvo = "MEZCLA MANUAL POLVO"
    Mez_maquina = "MEZCLA EN MAQUINA"
    mez_liquida = "MEZCLA LIQUIDA"
    Fabricacion = "FABRICACION DE ADEREZOS, JALEAS"
    
class PackagingTeams(str, Enum):
    Empaque1 = "Empaque 1"
    Empaque2 = "Empaque 2"
    Empaque3 = "Empaque 3"
    Empaque4 = "Empaque 4"
    Maquina1 = "MAQUINA 1"
    Maquina2 = "MAQUINA 2"

class PackagingActivities(str, Enum):
    Emp_mezcla = " EMPAQUE MANUAL MAS MEZCLA"
    Emp_grupo = "EMPAQUE MANUAL GRUPO"
    Emp_manual = "EMPAQUE MANUAL"
    Emp_semi = "EMPAQUE MAQUINA SEMI AUTOMATICA"
    Emp_auto = "EMPAQUE MAQUINA AUTOMATICA"

class MandatoryTasks(str, Enum):
    """Tareas obligatorias que deben incluirse en todas las programaciones"""
    REUNION_PREPARACION = "REUNION Y PREPARACION DE AREA"
    ALMUERZO = "ALMUERZO"
    LIMPIEZA = "LIMPIEZA"

class WorkingHours(BaseModel):
    """Configuración de horarios laborales"""
    monday_friday: Dict[str, time] = Field(
        default={
            "start": time(7, 0),
            "end": time(16, 0)
        },
        description="Horario de lunes a viernes: 7:00 - 16:00"
    )
    saturday: Dict[str, time] = Field(
        default={
            "start": time(7, 30),
            "end": time(11, 30)
        },
        description="Horario de sábado: 7:30 - 11:30"
    )
    sunday: Dict[str, time] = Field(
        default={
            "start": time(0, 0),
            "end": time(0, 0)
        },
        description="Domingo: No laboral"
    )

class ScheduleLimits(BaseModel):
    default: time = Field(default=time(14,40), description="Maximum time for default activities")
    weigh: time = Field(default=time(17,40), description="Maximum time for weigh activities")
    
schedule_limits = ScheduleLimits()

class MandatoryTaskDurations(BaseModel):
    """Duración en minutos de las tareas obligatorias por equipo"""
    reunion_preparacion: Dict[str, int] = Field(
        default={
            "MAQUINA 1": 20,
            "MAQUINA 2": 40,
            "default": 10
        },
        description="Duración en minutos de la reunión y preparación por equipo"
    )
    almuerzo: int = Field(default=60, description="Duración en minutos del almuerzo")
    limpieza: int = Field(default=20, description="Duración en minutos de la limpieza")

mandatory_task_durations = MandatoryTaskDurations()
working_hours = WorkingHours()

def get_reunion_preparacion_duration(team_name: str) -> int:
    """Obtiene la duración de la reunión y preparación para un equipo específico"""
    return mandatory_task_durations.reunion_preparacion.get(
        team_name, 
        mandatory_task_durations.reunion_preparacion["default"]
    )

def get_mandatory_tasks_info() -> Dict[str, Any]:
    """Retorna información completa de las tareas obligatorias"""
    return {
        "start_task": {
            "name": MandatoryTasks.REUNION_PREPARACION,
            "durations": mandatory_task_durations.reunion_preparacion
        },
        "end_tasks": [
            {
                "name": MandatoryTasks.ALMUERZO,
                "duration": mandatory_task_durations.almuerzo,
                "position": "penúltima"
            },
            {
                "name": MandatoryTasks.LIMPIEZA,
                "duration": mandatory_task_durations.limpieza,
                "position": "última"
            }
        ]
    }

def get_working_hours_for_day(weekday: int) -> Dict[str, time]:
    """
    Obtiene los horarios laborales para un día específico de la semana.
    
    Args:
        weekday: Día de la semana (0=Lunes, 5=Sábado, 6=Domingo)
        
    Returns:
        Dict con horarios de inicio y fin
    """
    if weekday == 5:  # Sábado
        return working_hours.saturday
    elif weekday == 6:  # Domingo
        return working_hours.sunday
    else:  # Lunes a Viernes (0-4)
        return working_hours.monday_friday

def is_working_day(weekday: int) -> bool:
    """
    Verifica si un día de la semana es laboral.
    
    Args:
        weekday: Día de la semana (0=Lunes, 6=Domingo)
        
    Returns:
        True si es día laboral, False en caso contrario
    """
    if weekday == 6:  # Domingo
        return False
    return True

def get_total_working_hours(weekday: int) -> float:
    """
    Calcula el total de horas laborales para un día específico.
    
    Args:
        weekday: Día de la semana (0=Lunes, 6=Domingo)
        
    Returns:
        Total de horas laborales como float
    """
    if not is_working_day(weekday):
        return 0.0
    
    hours = get_working_hours_for_day(weekday)
    start_time = hours["start"]
    end_time = hours["end"]
    
    # Calcular diferencia en horas
    start_minutes = start_time.hour * 60 + start_time.minute
    end_minutes = end_time.hour * 60 + end_time.minute
    
    total_minutes = end_minutes - start_minutes
    return round(total_minutes / 60.0, 2)
    
# Funciones de compatibilidad que redirigen al servicio
def extract_created_orders_data(created_orders: list) -> list:
    """
    Extrae solo los campos lote, quantity y code de las órdenes recién creadas.
    
    Args:
        created_orders: Lista de objetos Order de la base de datos
        
    Returns:
        Lista de diccionarios con solo lote, quantity y code
    """
    from app.services.weighing_task_service import WeighingTaskService
    return WeighingTaskService.extract_order_data(created_orders)

def extract_order_data_for_processing(order) -> dict:
    """
    Extrae solo los campos lote, quantity y code de una orden para procesamiento.
    
    Args:
        order: Objeto Order de la base de datos
        
    Returns:
        Diccionario con solo lote, quantity y code
    """
    order_data = {
        "lote": order.lote,
        "quantity": order.quantity,
        "code": order.code
    }
    return order_data

def get_orders_summary(created_orders: list) -> dict:
    """
    Genera un resumen simplificado de las órdenes recién creadas.
    
    Args:
        created_orders: Lista de objetos Order de la base de datos
        
    Returns:
        Diccionario con resumen básico de las órdenes creadas
    """
    if not created_orders:
        return {
            "total_orders": 0,
            "total_quantity": 0,
            "unique_codes": 0
        }
    
    total_quantity = 0
    unique_codes = set()
    
    for order in created_orders:
        # Sumar cantidad
        quantity = order.quantity or 0
        total_quantity += quantity
        
        # Códigos únicos
        if order.code:
            unique_codes.add(order.code)
        
    return {
        "total_orders": len(created_orders),
        "total_quantity": total_quantity,
        "unique_codes": len(unique_codes)
    }
    
# Funciones de compatibilidad que redirigen al servicio de pesado
def get_activities_by_code(code: str, db) -> dict:
    """Redirige al servicio de pesado"""
    from app.services.weighing_task_service import WeighingTaskService
    return WeighingTaskService.get_activities_by_code(code, db)

def get_activities_for_extracted_orders(extracted_orders: list, db) -> dict:
    """Redirige al servicio de pesado"""
    from app.services.weighing_task_service import WeighingTaskService
    return WeighingTaskService.get_activities_for_orders(extracted_orders, db)

def get_weighing_activities_for_orders(extracted_orders: list, db) -> dict:
    """Redirige al servicio de pesado"""
    from app.services.weighing_task_service import WeighingTaskService
    all_activities = WeighingTaskService.get_activities_for_orders(extracted_orders, db)
    weighing_activities = WeighingTaskService.filter_weighing_activities(all_activities)
    return {
        "all_activities": all_activities,
        "weighing_activities": weighing_activities,
        "total_orders_processed": len(extracted_orders)
    }

def get_weighing_activities_with_details(extracted_orders: list, db) -> dict:
    """Redirige al servicio de pesado"""
    from app.services.weighing_task_service import WeighingTaskService
    all_activities = WeighingTaskService.get_activities_for_orders(extracted_orders, db)
    weighing_activities = WeighingTaskService.filter_weighing_activities(all_activities)
    
    # Obtener detalles específicos para cada actividad de pesado
    weighing_activities_with_details = {}
    weighing_activities_by_code = weighing_activities.get("weighing_activities_by_code", {})
    
    for code, code_data in weighing_activities_by_code.items():
        weighing_activities_list = code_data.get("weighing_activities", [])
        activities_with_details = []
        
        for activity_data in weighing_activities_list:
            activity_name = activity_data.get("activity")
            if activity_name:
                activity_details = WeighingTaskService.get_activity_details_by_code_and_activity(code, activity_name, db)
                activities_with_details.append({
                    "activity_data": activity_data,
                    "activity_details": activity_details
                })
        
        if activities_with_details:
            weighing_activities_with_details[code] = {
                "code": code,
                "weighing_activities_with_details": activities_with_details,
                "total_weighing_activities": len(activities_with_details),
                "found": True
            }
    
    return {
        "all_activities": all_activities,
        "weighing_activities": weighing_activities,
        "weighing_activities_with_details": {
            "weighing_activities_with_details_by_code": weighing_activities_with_details,
            "total_codes_with_weighing_details": len(weighing_activities_with_details),
            "codes_with_weighing_details": list(weighing_activities_with_details.keys())
        },
        "total_orders_processed": len(extracted_orders)
    }
    
def get_activity_details_by_code_and_activity(code: str, activity: str, db) -> dict:
    """Redirige al servicio de pesado"""
    from app.services.weighing_task_service import WeighingTaskService
    return WeighingTaskService.get_activity_details_by_code_and_activity(code, activity, db)

def get_activity_details_with_minutes_calculation(code: str, activity: str, order_quantity: int, db) -> dict:
    """Redirige al servicio de pesado"""
    from app.services.weighing_task_service import WeighingTaskService
    activity_details_result = WeighingTaskService.get_activity_details_by_code_and_activity(code, activity, db)
    
    if not activity_details_result.get("success", False):
        return activity_details_result
    
    activity_details = activity_details_result.get("activity_details", {})
    performance = activity_details.get("performance")
    
    # Calcular minutos
    calculated_minutes = WeighingTaskService.calculate_minutes_from_performance_and_quantity(performance, order_quantity)
    
    # Calcular horas para mostrar en la fórmula
    hours_calculation = performance * order_quantity
    
    return {
        "success": True,
        "code": code,
        "activity": activity,
        "order_quantity": order_quantity,
        "activity_details": activity_details,
        "minutes_calculation": {
            "performance": performance,
            "quantity": order_quantity,
            "hours_calculation": hours_calculation,
            "calculated_minutes": calculated_minutes,
            "formula": f"{performance} horas * {order_quantity} = {hours_calculation} horas * 60 = {calculated_minutes} minutos (con ceiling)"
        },
        "message": f"Datos obtenidos y minutos calculados para código '{code}' y actividad '{activity}'"
    }

def get_weighing_activities_with_minutes_calculation(extracted_orders: list, db) -> dict:
    """Redirige al servicio de pesado"""
    from app.services.weighing_task_service import WeighingTaskService
    return WeighingTaskService.get_weighing_activities_with_minutes(extracted_orders, db)

def calculate_minutes_from_performance_and_quantity(performance: float, quantity: int) -> int:
    """Redirige al servicio de pesado"""
    from app.services.weighing_task_service import WeighingTaskService
    return WeighingTaskService.calculate_minutes_from_performance_and_quantity(performance, quantity)

def get_most_suitable_weighing_team(db) -> dict:
    """Redirige al servicio de pesado"""
    from app.services.weighing_task_service import WeighingTaskService
    return WeighingTaskService.get_most_suitable_weighing_team(db)

def get_most_suitable_weighing_team_with_available_programmings(db) -> dict:
    """Redirige al servicio de pesado"""
    from app.services.weighing_task_service import WeighingTaskService
    team_result = WeighingTaskService.get_most_suitable_weighing_team(db)
    
    if not team_result.get("success", False):
        return {
            "success": False,
            "message": "No se pudo obtener equipo idóneo para pesado",
            "team_data": team_result,
            "available_programmings": []
        }
    
    team_id = team_result.get("most_suitable_team", {}).get("id")
    available_programmings = WeighingTaskService.get_available_programmings_for_team(team_id, db)
    
    return {
        "success": True,
        "message": f"Equipo idóneo y programaciones obtenidas exitosamente",
        "team_data": team_result,
        "available_programmings": {
            "success": True,
            "message": "Programaciones disponibles obtenidas exitosamente",
            "team_id": team_id,
            "team_name": team_result.get("most_suitable_team", {}).get("name"),
            "programmings": available_programmings,
            "total_available_programmings": len(available_programmings)
        }
    }

def verify_programming_time_limit_simple(programmings: list, task_minutes: int, db, order_data: dict = None, activity_details: dict = None) -> dict:
    """Redirige al servicio de pesado"""
    from app.services.weighing_task_service import WeighingTaskService
    return WeighingTaskService.verify_programming_time_limit(programmings, task_minutes, db, order_data, activity_details)

def get_most_suitable_weighing_team_with_time_verification(db, task_minutes: int) -> dict:
    """Redirige al servicio de pesado"""
    from app.services.weighing_task_service import WeighingTaskService
    team_result = WeighingTaskService.get_most_suitable_weighing_team(db)
    
    if not team_result.get("success", False):
        return {
            "success": False,
            "message": "No se pudo obtener equipo idóneo y programaciones",
            "team_data": None,
            "available_programmings": None,
            "time_verification": None
        }
    
    team_id = team_result.get("most_suitable_team", {}).get("id")
    available_programmings = WeighingTaskService.get_available_programmings_for_team(team_id, db)
    
    if not available_programmings:
        return {
            "success": False,
            "message": "No hay programaciones disponibles para verificar",
            "team_data": team_result,
            "available_programmings": None,
            "time_verification": None
        }
    
    time_verification = WeighingTaskService.verify_programming_time_limit(available_programmings, task_minutes, db)
    
    return {
        "success": True,
        "message": "Equipo idóneo, programaciones y verificación de tiempo obtenidos exitosamente",
        "team_data": team_result,
        "available_programmings": {
            "success": True,
            "programmings": available_programmings,
            "total_available_programmings": len(available_programmings)
        },
        "time_verification": time_verification
    }

def create_weighing_task_for_order(extracted_orders: list, db) -> dict:
    """Redirige al servicio de pesado"""
    from app.services.weighing_task_service import WeighingTaskService
    return WeighingTaskService.create_weighing_tasks_for_orders(extracted_orders, db)

def create_weighing_tasks_for_multiple_orders(extracted_orders: list, db) -> dict:
    """Redirige al servicio de pesado"""
    from app.services.weighing_task_service import WeighingTaskService
    return WeighingTaskService.create_weighing_tasks_for_orders(extracted_orders, db)

# Funciones adicionales que redirigen al servicio
def get_most_suitable_weighing_team_with_available_programmings_sorted(db) -> dict:
    """Redirige al servicio de pesado"""
    return get_most_suitable_weighing_team_with_available_programmings(db)

def get_pesado_activity_for_order(order_data: dict, weighing_activities_with_minutes_data: dict) -> dict:
    """Redirige al servicio de pesado"""
    from app.services.weighing_task_service import WeighingTaskService
    return WeighingTaskService._get_pesado_activity_for_order(order_data, weighing_activities_with_minutes_data)

def update_programming_list_after_task_creation(programming_id: str, task_minutes: int, db) -> list:
    """Redirige al servicio de pesado"""
    from app.services.weighing_task_service import WeighingTaskService
    team_result = WeighingTaskService.get_most_suitable_weighing_team(db)
    if not team_result.get("success"):
        return []
    
    team_id = team_result.get("most_suitable_team", {}).get("id")
    if not team_id:
        return []
    
    return WeighingTaskService.get_available_programmings_for_team(team_id, db)

def create_single_weighing_task(order_data: dict, task_minutes: int, activity_details: dict, available_programmings: list, db) -> dict:
    """Redirige al servicio de pesado"""
    from app.services.weighing_task_service import WeighingTaskService
    time_verification_data = WeighingTaskService.verify_programming_time_limit(
        available_programmings, task_minutes, db, order_data, activity_details
    )
    
    if not time_verification_data.get("success"):
        return {
            "success": False,
            "message": f"No se pudo encontrar una programación adecuada para la orden {order_data.get('lote')}",
            "order_data": order_data
        }
    
    if time_verification_data.get("order_task_created"):
        return {
            "success": True,
            "message": f"Tarea de pesado creada exitosamente para orden {order_data.get('lote')}",
            "order_data": order_data,
            "selected_programming": time_verification_data.get("selected_programming"),
            "order_task": time_verification_data.get("order_task_created")
        }
    else:
        return {
            "success": False,
            "message": f"Programación seleccionada pero no se pudo crear la tarea para orden {order_data.get('lote')}",
            "order_data": order_data,
            "selected_programming": time_verification_data.get("selected_programming")
        }

# ============================================================================
# FUNCIONES DE COMPATIBILIDAD PARA EL SERVICIO DE FABRICACIÓN
# ============================================================================

def get_fabrication_activities_by_code(code: str, db) -> dict:
    """Redirige al servicio de fabricación"""
    from app.services.fabrication_task_service import FabricationTaskService
    return FabricationTaskService.get_activities_by_code(code, db)

def get_fabrication_activities_for_extracted_orders(extracted_orders: list, db) -> dict:
    """Redirige al servicio de fabricación"""
    from app.services.fabrication_task_service import FabricationTaskService
    return FabricationTaskService.get_activities_for_orders(extracted_orders, db)

def get_fabrication_activities_for_orders(extracted_orders: list, db) -> dict:
    """Redirige al servicio de fabricación"""
    from app.services.fabrication_task_service import FabricationTaskService
    all_activities = FabricationTaskService.get_activities_for_orders(extracted_orders, db)
    fabrication_activities = FabricationTaskService.filter_fabrication_activities(all_activities)
    return {
        "all_activities": all_activities,
        "fabrication_activities": fabrication_activities,
        "total_orders_processed": len(extracted_orders)
    }

def get_fabrication_activities_with_details(extracted_orders: list, db) -> dict:
    """Redirige al servicio de fabricación"""
    from app.services.fabrication_task_service import FabricationTaskService
    all_activities = FabricationTaskService.get_activities_for_orders(extracted_orders, db)
    fabrication_activities = FabricationTaskService.filter_fabrication_activities(all_activities)
    
    # Obtener detalles específicos para cada actividad de fabricación
    fabrication_activities_with_details = {}
    fabrication_activities_by_code = fabrication_activities.get("fabrication_activities_by_code", {})
    
    for code, code_data in fabrication_activities_by_code.items():
        fabrication_activities_list = code_data.get("fabrication_activities", [])
        activities_with_details = []
        
        for activity_data in fabrication_activities_list:
            activity_name = activity_data.get("activity")
            if activity_name:
                activity_details = FabricationTaskService.get_activity_details_by_code_and_activity(code, activity_name, db)
                activities_with_details.append({
                    "activity_data": activity_data,
                    "activity_details": activity_details
                })
        
        if activities_with_details:
            fabrication_activities_with_details[code] = {
                "code": code,
                "fabrication_activities_with_details": activities_with_details,
                "total_fabrication_activities": len(activities_with_details),
                "found": True
            }
    
    return {
        "all_activities": all_activities,
        "fabrication_activities": fabrication_activities,
        "fabrication_activities_with_details": {
            "fabrication_activities_with_details_by_code": fabrication_activities_with_details,
            "total_codes_with_fabrication_details": len(fabrication_activities_with_details),
            "codes_with_fabrication_details": list(fabrication_activities_with_details.keys())
        },
        "total_orders_processed": len(extracted_orders)
    }

def get_fabrication_activity_details_by_code_and_activity(code: str, activity: str, db) -> dict:
    """Redirige al servicio de fabricación"""
    from app.services.fabrication_task_service import FabricationTaskService
    return FabricationTaskService.get_activity_details_by_code_and_activity(code, activity, db)

def get_fabrication_activity_details_with_minutes_calculation(code: str, activity: str, order_quantity: int, db) -> dict:
    """Redirige al servicio de fabricación"""
    from app.services.fabrication_task_service import FabricationTaskService
    activity_details_result = FabricationTaskService.get_activity_details_by_code_and_activity(code, activity, db)
    
    if not activity_details_result.get("success", False):
        return activity_details_result
    
    activity_details = activity_details_result.get("activity_details", {})
    performance = activity_details.get("performance")
    
    # Calcular minutos
    calculated_minutes = FabricationTaskService.calculate_minutes_from_performance_and_quantity(performance, order_quantity)
    
    # Calcular horas para mostrar en la fórmula
    hours_calculation = performance * order_quantity
    
    return {
        "success": True,
        "code": code,
        "activity": activity,
        "order_quantity": order_quantity,
        "activity_details": activity_details,
        "minutes_calculation": {
            "performance": performance,
            "quantity": order_quantity,
            "hours_calculation": hours_calculation,
            "calculated_minutes": calculated_minutes,
            "formula": f"{performance} horas * {order_quantity} = {hours_calculation} horas * 60 = {calculated_minutes} minutos (con ceiling)"
        },
        "message": f"Datos obtenidos y minutos calculados para código '{code}' y actividad '{activity}'"
    }

def get_fabrication_activities_with_minutes_calculation(extracted_orders: list, db) -> dict:
    """Redirige al servicio de fabricación"""
    from app.services.fabrication_task_service import FabricationTaskService
    return FabricationTaskService.get_fabrication_activities_with_minutes(extracted_orders, db)

def calculate_fabrication_minutes_from_performance_and_quantity(performance: float, quantity: int) -> int:
    """Redirige al servicio de fabricación"""
    from app.services.fabrication_task_service import FabricationTaskService
    return FabricationTaskService.calculate_minutes_from_performance_and_quantity(performance, quantity)

def get_most_suitable_fabrication_team(db) -> dict:
    """Redirige al servicio de fabricación"""
    from app.services.fabrication_task_service import FabricationTaskService
    return FabricationTaskService.get_most_suitable_fabrication_team(db)

def get_most_suitable_fabrication_team_with_available_programmings(db) -> dict:
    """Redirige al servicio de fabricación"""
    from app.services.fabrication_task_service import FabricationTaskService
    team_result = FabricationTaskService.get_most_suitable_fabrication_team(db)
    
    if not team_result.get("success", False):
        return {
            "success": False,
            "message": "No se pudo obtener equipo idóneo para fabricación",
            "team_data": team_result,
            "available_programmings": []
        }
    
    team_id = team_result.get("most_suitable_team", {}).get("id")
    available_programmings = FabricationTaskService.get_available_programmings_for_team(team_id, db)
    
    return {
        "success": True,
        "message": f"Equipo idóneo y programaciones obtenidas exitosamente",
        "team_data": team_result,
        "available_programmings": {
            "success": True,
            "message": "Programaciones disponibles obtenidas exitosamente",
            "team_id": team_id,
            "team_name": team_result.get("most_suitable_team", {}).get("name"),
            "programmings": available_programmings,
            "total_available_programmings": len(available_programmings)
        }
    }

def verify_fabrication_programming_time_limit_simple(programmings: list, task_minutes: int, db, order_data: dict = None, activity_details: dict = None) -> dict:
    """Redirige al servicio de fabricación"""
    from app.services.fabrication_task_service import FabricationTaskService
    return FabricationTaskService.verify_programming_time_limit(programmings, task_minutes, db, order_data, activity_details)

def get_most_suitable_fabrication_team_with_time_verification(db, task_minutes: int) -> dict:
    """Redirige al servicio de fabricación"""
    from app.services.fabrication_task_service import FabricationTaskService
    team_result = FabricationTaskService.get_most_suitable_fabrication_team(db)
    
    if not team_result.get("success", False):
        return {
            "success": False,
            "message": "No se pudo obtener equipo idóneo y programaciones",
            "team_data": None,
            "available_programmings": None,
            "time_verification": None
        }
    
    team_id = team_result.get("most_suitable_team", {}).get("id")
    available_programmings = FabricationTaskService.get_available_programmings_for_team(team_id, db)
    
    if not available_programmings:
        return {
            "success": False,
            "message": "No hay programaciones disponibles para verificar",
            "team_data": team_result,
            "available_programmings": None,
            "time_verification": None
        }
    
    time_verification = FabricationTaskService.verify_programming_time_limit(available_programmings, task_minutes, db)
    
    return {
        "success": True,
        "message": "Equipo idóneo, programaciones y verificación de tiempo obtenidos exitosamente",
        "team_data": team_result,
        "available_programmings": {
            "success": True,
            "programmings": available_programmings,
            "total_available_programmings": len(available_programmings)
        },
        "time_verification": time_verification
    }

def create_fabrication_task_for_order(extracted_orders: list, db) -> dict:
    """Redirige al servicio de fabricación"""
    from app.services.fabrication_task_service import FabricationTaskService
    return FabricationTaskService.create_fabrication_tasks_for_orders(extracted_orders, db)

def create_fabrication_tasks_for_multiple_orders(extracted_orders: list, db) -> dict:
    """Redirige al servicio de fabricación"""
    from app.services.fabrication_task_service import FabricationTaskService
    return FabricationTaskService.create_fabrication_tasks_for_orders(extracted_orders, db)

def get_most_suitable_fabrication_team_with_available_programmings_sorted(db) -> dict:
    """Redirige al servicio de fabricación"""
    return get_most_suitable_fabrication_team_with_available_programmings(db)

def get_fabrication_activity_for_order(order_data: dict, fabrication_activities_with_minutes_data: dict) -> dict:
    """Redirige al servicio de fabricación"""
    from app.services.fabrication_task_service import FabricationTaskService
    return FabricationTaskService._get_fabrication_activity_for_order(order_data, fabrication_activities_with_minutes_data)

def update_fabrication_programming_list_after_task_creation(programming_id: str, task_minutes: int, db) -> list:
    """Redirige al servicio de fabricación"""
    from app.services.fabrication_task_service import FabricationTaskService
    team_result = FabricationTaskService.get_most_suitable_fabrication_team(db)
    if not team_result.get("success"):
        return []
    
    team_id = team_result.get("most_suitable_team", {}).get("id")
    if not team_id:
        return []
    
    return FabricationTaskService.get_available_programmings_for_team(team_id, db)

def create_single_fabrication_task(order_data: dict, task_minutes: int, activity_details: dict, available_programmings: list, db) -> dict:
    """Redirige al servicio de fabricación"""
    from app.services.fabrication_task_service import FabricationTaskService
    time_verification_data = FabricationTaskService.verify_programming_time_limit(
        available_programmings, task_minutes, db, order_data, activity_details
    )
    
    if not time_verification_data.get("success"):
        return {
            "success": False,
            "message": f"No se pudo encontrar una programación adecuada para la orden {order_data.get('lote')}",
            "order_data": order_data
        }
    
    if time_verification_data.get("order_task_created"):
        return {
            "success": True,
            "message": f"Tarea de fabricación creada exitosamente para orden {order_data.get('lote')}",
            "order_data": order_data,
            "selected_programming": time_verification_data.get("selected_programming"),
            "order_task": time_verification_data.get("order_task_created")
        }
    else:
        return {
            "success": False,
            "message": f"Programación seleccionada pero no se pudo crear la tarea para orden {order_data.get('lote')}",
            "order_data": order_data,
            "selected_programming": time_verification_data.get("selected_programming")
        } 