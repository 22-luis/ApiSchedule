from typing import List, Dict, Any
from pydantic import BaseModel, Field
from datetime import time
from sqlalchemy.orm import Session
from app.modules.core.models.team import Team
from app.modules.programming.models.programming import Programming, ProgrammingStatus
from app.shared.core.enums import (
    PackagingActivities, 
    ManufacturingActivities, 
    WeighingActivities
)
from app.modules.programming.services.factory import TaskServiceFactory

class TaskConfiguration:
    class WorkingHours(BaseModel):
        monday_friday: Dict[str, time] = Field(
            default={"start": time(7, 0), "end": time(16, 0)},
            description="Horario de lunes a viernes: 7:00 - 16:00"
        )
        saturday: Dict[str, time] = Field(
            default={"start": time(7, 30), "end": time(11, 30)},
            description="Horario de sábado: 7:30 - 11:30"
        )
        sunday: Dict[str, time] = Field(
            default={"start": time(0, 0), "end": time(0, 0)},
            description="Domingo: No laboral"
        )

    class ScheduleLimits(BaseModel):
        default: time = Field(default=time(14, 40), description="Maximum time for default activities")
        weigh: time = Field(default=time(17, 40), description="Maximum time for weigh activities")

    def __init__(self):
        self.working_hours = self.WorkingHours()
        self.schedule_limits = self.ScheduleLimits()

    def get_working_hours_for_day(self, weekday: int) -> Dict[str, time]:
        if weekday == 5:  # Sábado
            return self.working_hours.saturday
        elif weekday == 6:  # Domingo
            return self.working_hours.sunday
        else:  # Lunes a Viernes (0-4)
            return self.working_hours.monday_friday

    def is_working_day(self, weekday: int) -> bool:
        return weekday != 6  # Domingo

    def get_total_working_hours(self, weekday: int) -> float:
        if not self.is_working_day(weekday):
            return 0.0
        
        hours = self.get_working_hours_for_day(weekday)
        start_time = hours["start"]
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
    return weighing_service.get_activities_by_code(code, db)

def get_activities_for_extracted_orders(extracted_orders: list, db) -> dict:
    return weighing_service.get_activities_for_orders(extracted_orders, db)

def get_weighing_activities_for_orders(extracted_orders: list, db) -> dict:
    all_activities = weighing_service.get_activities_for_orders(extracted_orders, db)
    weighing_activities = weighing_service.filter_weighing_activities(all_activities)
    return {
        "all_activities": all_activities,
        "weighing_activities": weighing_activities,
        "total_orders_processed": len(extracted_orders)
    }

def get_weighing_activities_with_details(extracted_orders: list, db) -> dict:
    all_activities = weighing_service.get_activities_for_orders(extracted_orders, db)
    weighing_activities = weighing_service.filter_weighing_activities(all_activities)
    
    weighing_activities_with_details = {}
    weighing_activities_by_code = weighing_activities.get("weighing_activities_by_code", {})
    
    for code, code_data in weighing_activities_by_code.items():
        weighing_activities_list = code_data.get("weighing_activities", [])
        activities_with_details = []
        
        for activity_data in weighing_activities_list:
            activity_name = activity_data.get("activity")
            if activity_name:
                activity_details = weighing_service.get_activity_details_by_code_and_activity(code, activity_name, db)
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
    return weighing_service.get_activity_details_by_code_and_activity(code, activity, db)

def get_activity_details_with_minutes_calculation(code: str, activity: str, order_quantity: int, db) -> dict:
    activity_details_result = weighing_service.get_activity_details_by_code_and_activity(code, activity, db)
    
    if not activity_details_result.get("success", False):
        return activity_details_result
    
    activity_details = activity_details_result.get("activity_details", {})
    performance = activity_details.get("performance")
    
    calculated_minutes = weighing_service.calculate_minutes_from_performance_and_quantity(performance, order_quantity)
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
    return weighing_service.get_weighing_activities_with_minutes(extracted_orders, db)

def calculate_minutes_from_performance_and_quantity(performance: float, quantity: int) -> int:
    return weighing_service.calculate_minutes_from_performance_and_quantity(performance, quantity)

def get_most_suitable_weighing_team(db) -> dict:
    return weighing_service.get_most_suitable_weighing_team(db)

def get_most_suitable_weighing_team_with_available_programmings(db) -> dict:
    team_result = weighing_service.get_most_suitable_team(db)
    
    if not team_result.get("success", False):
        return {
            "success": False,
            "message": "No se pudo obtener equipo idóneo para pesado",
            "team_data": team_result,
            "available_programmings": []
        }
    
    team_id = team_result.get("most_suitable_team", {}).get("id")
    available_programmings = weighing_service.get_available_programmings_for_team(team_id, db)
    
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
    return weighing_service.verify_programming_time_limit(programmings, task_minutes, db, order_data, activity_details)

def get_most_suitable_weighing_team_with_time_verification(db, task_minutes: int) -> dict:
    team_result = weighing_service.get_most_suitable_team(db)
    
    if not team_result.get("success", False):
        return {
            "success": False,
            "message": "No se pudo obtener equipo idóneo y programaciones",
            "team_data": None,
            "available_programmings": None,
            "time_verification": None
        }
    
    team_id = team_result.get("most_suitable_team", {}).get("id")
    available_programmings = weighing_service.get_available_programmings_for_team(team_id, db)
    
    if not available_programmings:
        return {
            "success": False,
            "message": "No hay programaciones disponibles para verificar",
            "team_data": team_result,
            "available_programmings": None,
            "time_verification": None
        }
    
    time_verification = weighing_service.verify_programming_time_limit(available_programmings, task_minutes, db)
    
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
    return weighing_service.create_weighing_tasks_for_orders(extracted_orders, db)

def create_weighing_tasks_for_multiple_orders(extracted_orders: list, db) -> dict:
    return weighing_service.create_weighing_tasks_for_orders(extracted_orders, db)

# Funciones adicionales que redirigen al servicio
def get_most_suitable_weighing_team_with_available_programmings_sorted(db) -> dict:
    return get_most_suitable_weighing_team_with_available_programmings(db)

def get_pesado_activity_for_order(order_data: dict, weighing_activities_with_minutes_data: dict) -> dict:
    return weighing_service._get_pesado_activity_for_order(order_data, weighing_activities_with_minutes_data)

def update_programming_list_after_task_creation(programming_id: str, task_minutes: int, db) -> list:
    team_result = weighing_service.get_most_suitable_weighing_team(db)
    if not team_result.get("success"):
        return []
    
    team_id = team_result.get("most_suitable_team", {}).get("id")
    if not team_id:
        return []
    
    return weighing_service.get_available_programmings_for_team(team_id, db)

def create_single_weighing_task(order_data: dict, task_minutes: int, activity_details: dict, available_programmings: list, db) -> dict:
    time_verification_data = weighing_service.verify_programming_time_limit(
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
    return fabrication_service.get_activities_by_code(code, db)

def get_fabrication_activities_for_extracted_orders(extracted_orders: list, db) -> dict:
    return fabrication_service.get_activities_for_orders(extracted_orders, db)

def get_fabrication_activities_for_orders(extracted_orders: list, db) -> dict:
    all_activities = fabrication_service.get_activities_for_orders(extracted_orders, db)
    fabrication_activities = fabrication_service.filter_fabrication_activities(all_activities)
    return {
        "all_activities": all_activities,
        "fabrication_activities": fabrication_activities,
        "total_orders_processed": len(extracted_orders)
    }

def get_fabrication_activities_with_details(extracted_orders: list, db) -> dict:
    all_activities = fabrication_service.get_activities_for_orders(extracted_orders, db)
    fabrication_activities = fabrication_service.filter_fabrication_activities(all_activities)
    
    fabrication_activities_with_details = {}
    fabrication_activities_by_code = fabrication_activities.get("fabrication_activities_by_code", {})
    
    for code, code_data in fabrication_activities_by_code.items():
        fabrication_activities_list = code_data.get("fabrication_activities", [])
        activities_with_details = []
        
        for activity_data in fabrication_activities_list:
            activity_name = activity_data.get("activity")
            if activity_name:
                activity_details = fabrication_service.get_activity_details_by_code_and_activity(code, activity_name, db)
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
    return fabrication_service.get_activity_details_by_code_and_activity(code, activity, db)

def get_fabrication_activity_details_with_minutes_calculation(code: str, activity: str, order_quantity: int, db) -> dict:
    activity_details_result = fabrication_service.get_activity_details_by_code_and_activity(code, activity, db)
    
    if not activity_details_result.get("success", False):
        return activity_details_result
    
    activity_details = activity_details_result.get("activity_details", {})
    performance = activity_details.get("performance")
    
    calculated_minutes = fabrication_service.calculate_minutes_from_performance_and_quantity(performance, order_quantity)
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
    return fabrication_service.get_fabrication_activities_with_minutes(extracted_orders, db)

def calculate_fabrication_minutes_from_performance_and_quantity(performance: float, quantity: int) -> int:
    return fabrication_service.calculate_minutes_from_performance_and_quantity(performance, quantity)

def get_most_suitable_fabrication_team(db) -> dict:
    return fabrication_service.get_most_suitable_fabrication_team(db)

def get_most_suitable_fabrication_team_with_available_programmings(db) -> dict:
    team_result = fabrication_service.get_most_suitable_team(db)
    
    if not team_result.get("success", False):
        return {
            "success": False,
            "message": "No se pudo obtener equipo idóneo para fabricación",
            "team_data": team_result,
            "available_programmings": []
        }
    
    return {
        "success": True,
        "message": f"Equipos de fabricación obtenidos exitosamente",
        "team_data": team_result,
        "available_programmings": {
            "success": True,
            "message": "Equipos de fabricación disponibles",
            "total_fabrication_teams": team_result.get("total_fabrication_teams", 0)
        }
    }

def verify_fabrication_programming_time_limit_simple(programmings: list, task_minutes: int, db, order_data: dict = None, activity_details: dict = None) -> dict:
    return fabrication_service.verify_programming_time_limit(programmings, task_minutes, db, order_data, activity_details)

def get_most_suitable_fabrication_team_with_time_verification(db, task_minutes: int) -> dict:
    team_result = fabrication_service.get_most_suitable_fabrication_team(db)
    
    if not team_result.get("success", False):
        return {
            "success": False,
            "message": "No se pudo obtener equipo idóneo y programaciones",
            "team_data": None,
            "available_programmings": None,
            "time_verification": None
        }
    
    team_id = team_result.get("most_suitable_team", {}).get("id")
    available_programmings = fabrication_service.get_available_programmings_for_team(team_id, db)
    
    if not available_programmings:
        return {
            "success": False,
            "message": "No hay programaciones disponibles para verificar",
            "team_data": team_result,
            "available_programmings": None,
            "time_verification": None
        }
    
    time_verification = fabrication_service.verify_programming_time_limit(available_programmings, task_minutes, db)
    
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
    return fabrication_service.create_fabrication_tasks_for_orders(extracted_orders, db)

def create_fabrication_tasks_for_multiple_orders(extracted_orders: list, db) -> dict:
    return fabrication_service.create_fabrication_tasks_for_orders(extracted_orders, db)

def get_most_suitable_fabrication_team_with_available_programmings_sorted(db) -> dict:
    return get_most_suitable_fabrication_team_with_available_programmings(db)

def get_fabrication_activity_for_order(order_data: dict, fabrication_activities_with_minutes_data: dict) -> dict:
    return fabrication_service._get_fabrication_activity_for_order(order_data, fabrication_activities_with_minutes_data)

def update_fabrication_programming_list_after_task_creation(programming_id: str, task_minutes: int, db) -> list:
    team_result = fabrication_service.get_most_suitable_fabrication_team(db)
    if not team_result.get("success"):
        return []
    
    team_id = team_result.get("most_suitable_team", {}).get("id")
    if not team_id:
        return []
    
    return fabrication_service.get_available_programmings_for_team(team_id, db)

def create_single_fabrication_task(order_data: dict, task_minutes: int, activity_details: dict, available_programmings: list, db) -> dict:
    time_verification_data = fabrication_service.verify_programming_time_limit(
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

# ============================================================================
# FUNCIONES DE COMPATIBILIDAD PARA EL SERVICIO DE EMPAQUE
# ============================================================================

def get_packaging_activities_by_code(code: str, db) -> dict:
    return packaging_service.get_activities_by_code(code, db)

def get_packaging_activities_for_extracted_orders(extracted_orders: list, db) -> dict:
    return packaging_service.get_activities_for_orders(extracted_orders, db)

def get_packaging_activities_for_orders(extracted_orders: list, db) -> dict:
    all_activities = packaging_service.get_activities_for_orders(extracted_orders, db)
    packaging_activities = packaging_service.filter_packaging_activities(all_activities)
    return {
        "all_activities": all_activities,
        "packaging_activities": packaging_activities,
        "total_orders_processed": len(extracted_orders)
    }

def get_packaging_activities_with_details(extracted_orders: list, db) -> dict:
    all_activities = packaging_service.get_activities_for_orders(extracted_orders, db)
    packaging_activities = packaging_service.filter_packaging_activities(all_activities)
    
    packaging_activities_with_details = {}
    packaging_activities_by_code = packaging_activities.get("packaging_activities_by_code", {})
    
    for code, code_data in packaging_activities_by_code.items():
        packaging_activities_list = code_data.get("packaging_activities", [])
        activities_with_details = []
        
        for activity_data in packaging_activities_list:
            activity_name = activity_data.get("activity")
            if activity_name:
                activity_details = packaging_service.get_activity_details_by_code_and_activity(code, activity_name, db)
                activities_with_details.append({
                    "activity_data": activity_data,
                    "activity_details": activity_details
                })
        
        if activities_with_details:
            packaging_activities_with_details[code] = {
                "code": code,
                "packaging_activities_with_details": activities_with_details,
                "total_packaging_activities": len(activities_with_details),
                "found": True
            }
    
    return {
        "all_activities": all_activities,
        "packaging_activities": packaging_activities,
        "packaging_activities_with_details": {
            "packaging_activities_with_details_by_code": packaging_activities_with_details,
            "total_codes_with_packaging_details": len(packaging_activities_with_details),
            "codes_with_packaging_details": list(packaging_activities_with_details.keys())
        },
        "total_orders_processed": len(extracted_orders)
    }

def get_packaging_activity_details_by_code_and_activity(code: str, activity: str, db) -> dict:
    return packaging_service.get_activity_details_by_code_and_activity(code, activity, db)

def get_packaging_activity_details_with_minutes_calculation(code: str, activity: str, order_quantity: int, db) -> dict:
    activity_details_result = packaging_service.get_activity_details_by_code_and_activity(code, activity, db)
    
    if not activity_details_result.get("success", False):
        return activity_details_result
    
    activity_details = activity_details_result.get("activity_details", {})
    performance = activity_details.get("performance")
    
    calculated_minutes = packaging_service.calculate_minutes_from_performance_and_quantity(performance, order_quantity)
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

def get_packaging_activities_with_minutes_calculation(extracted_orders: list, db) -> dict:
    return packaging_service.get_packaging_activities_with_minutes(extracted_orders, db)

def calculate_packaging_minutes_from_performance_and_quantity(performance: float, quantity: int) -> int:
    return packaging_service.calculate_minutes_from_performance_and_quantity(performance, quantity)

def get_most_suitable_packaging_team(db) -> dict:
    return packaging_service.get_most_suitable_team(db)

def get_most_suitable_packaging_team_with_available_programmings(db) -> dict:
    team_result = packaging_service.get_most_suitable_team(db)
    
    if not team_result.get("success", False):
        return {
            "success": False,
            "message": "No se pudo obtener equipo idóneo para empaque",
            "team_data": team_result,
            "available_programmings": []
        }
    
    return {
        "success": True,
        "message": f"Equipos de empaque obtenidos exitosamente",
        "team_data": team_result,
        "available_programmings": {
            "success": True,
            "message": "Equipos de empaque disponibles",
            "total_packaging_teams": team_result.get("total_packaging_teams", 0)
        }
    }

def verify_packaging_programming_time_limit_simple(programmings: list, task_minutes: int, db, order_data: dict = None, activity_details: dict = None) -> dict:
    return packaging_service.verify_programming_time_limit(programmings, task_minutes, db, order_data, activity_details)

def get_most_suitable_packaging_team_with_time_verification(db, task_minutes: int) -> dict:
    team_result = packaging_service.get_most_suitable_team(db)
    
    if not team_result.get("success", False):
        return {
            "success": False,
            "message": "No se pudo obtener equipo idóneo y programaciones",
            "team_data": None,
            "available_programmings": None,
            "time_verification": None
        }
    
    team_id = team_result.get("most_suitable_team", {}).get("id")
    available_programmings = packaging_service.get_available_programmings_for_team(team_id, db)
    
    if not available_programmings:
        return {
            "success": False,
            "message": "No hay programaciones disponibles para verificar",
            "team_data": team_result,
            "available_programmings": None,
            "time_verification": None
        }
    
    time_verification = packaging_service.verify_programming_time_limit(available_programmings, task_minutes, db)
    
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

def create_packaging_task_for_order(extracted_orders: list, db) -> dict:
    return packaging_service.create_packaging_tasks_for_orders(extracted_orders, db)

def create_packaging_tasks_for_multiple_orders(extracted_orders: list, db) -> dict:
    return packaging_service.create_packaging_tasks_for_orders(extracted_orders, db)

def get_most_suitable_packaging_team_with_available_programmings_sorted(db) -> dict:
    return get_most_suitable_packaging_team_with_available_programmings(db)

def get_packaging_activity_for_order(order_data: dict, packaging_activities_with_minutes_data: dict) -> dict:
    return packaging_service.get_activity_for_order(order_data, packaging_activities_with_minutes_data)

def update_packaging_programming_list_after_task_creation(programming_id: str, task_minutes: int, db) -> list:
    team_result = packaging_service.get_most_suitable_team(db)
    if not team_result.get("success"):
        return []
    
    team_id = team_result.get("most_suitable_team", {}).get("id")
    if not team_id:
        return []
    
    return packaging_service.get_available_programmings_for_team(team_id, db)

def create_single_packaging_task(order_data: dict, task_minutes: int, activity_details: dict, available_programmings: list, db) -> dict:
    time_verification_data = packaging_service.verify_programming_time_limit(
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
            "message": f"Tarea de empaque creada exitosamente para orden {order_data.get('lote')}",
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