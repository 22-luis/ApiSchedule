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
    
def extract_created_orders_data(created_orders: list) -> list:
    """
    Extrae solo los campos lote, quantity y code de las órdenes recién creadas.
    
    Args:
        created_orders: Lista de objetos Order de la base de datos
        
    Returns:
        Lista de diccionarios con solo lote, quantity y code
    """
    print(f"[DEBUG] extract_created_orders_data: Iniciando extracción de {len(created_orders)} órdenes")
    extracted_data = []
    
    for i, order in enumerate(created_orders):
        order_data = {
            "lote": order.lote,
            "quantity": order.quantity,
            "code": order.code
        }
        extracted_data.append(order_data)
        print(f"[DEBUG] Orden {i+1}: lote={order.lote}, quantity={order.quantity}, code={order.code}")
    
    print(f"[DEBUG] extract_created_orders_data: Extracción completada. {len(extracted_data)} órdenes procesadas")
    print(f"[DEBUG] Datos extraídos: {extracted_data}")
    return extracted_data

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
    print(f"[DEBUG] extract_order_data_for_processing: lote={order.lote}, quantity={order.quantity}, code={order.code}")
    return order_data

def get_orders_summary(created_orders: list) -> dict:
    """
    Genera un resumen simplificado de las órdenes recién creadas.
    
    Args:
        created_orders: Lista de objetos Order de la base de datos
        
    Returns:
        Diccionario con resumen básico de las órdenes creadas
    """
    print(f"[DEBUG] get_orders_summary: Iniciando resumen de {len(created_orders)} órdenes")
    
    if not created_orders:
        print("[DEBUG] get_orders_summary: No hay órdenes para procesar")
        return {
            "total_orders": 0,
            "total_quantity": 0,
            "unique_codes": 0
        }
    
    total_quantity = 0
    unique_codes = set()
    
    for i, order in enumerate(created_orders):
        # Sumar cantidad
        quantity = order.quantity or 0
        total_quantity += quantity
        
        # Códigos únicos
        if order.code:
            unique_codes.add(order.code)
        
        print(f"[DEBUG] Orden {i+1} en resumen: lote={order.lote}, quantity={quantity}, code={order.code}")
    
    summary = {
        "total_orders": len(created_orders),
        "total_quantity": total_quantity,
        "unique_codes": len(unique_codes)
    }
    
    print(f"[DEBUG] get_orders_summary: Resumen final - {summary}")
    return summary

def get_activities_by_code(code: str, db) -> dict:
    """
    Obtiene todas las actividades para un código específico.
    
    Args:
        code: Código de la orden
        db: Sesión de base de datos
        
    Returns:
        Diccionario con las actividades del código
    """
    from app.models.code import Code
    
    print(f"[DEBUG] get_activities_by_code: Buscando actividades para código '{code}'")
    
    code_objs = db.query(Code).filter(Code.code == code).all()
    
    if not code_objs:
        print(f"[DEBUG] get_activities_by_code: No se encontraron actividades para código '{code}'")
        return {
            "code": code,
            "activities": [],
            "total_activities": 0,
            "found": False
        }
    
    activities = []
    for i, code_obj in enumerate(code_objs):
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
        print(f"[DEBUG] Actividad {i+1}: {activity_data['activity']} - {activity_data['description']}")
    
    result = {
        "code": code,
        "activities": activities,
        "total_activities": len(activities),
        "found": True
    }
    
    print(f"[DEBUG] get_activities_by_code: Encontradas {len(activities)} actividades para código '{code}'")
    return result

def get_activities_for_extracted_orders(extracted_orders: list, db) -> dict:
    """
    Obtiene las actividades para todas las órdenes extraídas.
    
    Args:
        extracted_orders: Lista de órdenes extraídas (con lote, quantity, code)
        db: Sesión de base de datos
        
    Returns:
        Diccionario con actividades organizadas por código
    """
    print(f"[DEBUG] get_activities_for_extracted_orders: Procesando {len(extracted_orders)} órdenes")
    
    activities_by_code = {}
    unique_codes = set()
    
    for order in extracted_orders:
        code = order.get('code')
        if code:
            unique_codes.add(code)
    
    print(f"[DEBUG] get_activities_for_extracted_orders: Códigos únicos encontrados: {list(unique_codes)}")
    
    for code in unique_codes:
        activities_data = get_activities_by_code(code, db)
        activities_by_code[code] = activities_data
    
    result = {
        "activities_by_code": activities_by_code,
        "total_codes_processed": len(unique_codes),
        "codes_processed": list(unique_codes)
    }
    
    print(f"[DEBUG] get_activities_for_extracted_orders: Procesamiento completado para {len(unique_codes)} códigos")
    return result

def filter_weighing_activities(activities_data: dict) -> dict:
    """
    Filtra las actividades para obtener solo las relacionadas con pesado.
    
    Args:
        activities_data: Diccionario con todas las actividades organizadas por código
        
    Returns:
        Diccionario con solo las actividades de pesado organizadas por código
    """
    print(f"[DEBUG] filter_weighing_activities: Filtrando actividades de pesado")
    weighing_activities_by_code = {}
    
    activities_by_code = activities_data.get("activities_by_code", {})
    for code, code_data in activities_by_code.items():
        print(f"[DEBUG] filter_weighing_activities: Procesando código '{code}'")
        activities = code_data.get("activities", [])
        weighing_activities = []
        
        for activity in activities:
            activity_name = activity.get("activity", "").upper()
            print(f"[DEBUG] filter_weighing_activities: Revisando actividad '{activity_name}'")
            
            # Buscar actividades relacionadas con pesado
            if any(keyword in activity_name for keyword in ["PESADO", "PESAR", "PESO", "BALANZA", "WEIGHING"]):
                weighing_activities.append(activity)
                print(f"[DEBUG] filter_weighing_activities: Actividad '{activity_name}' identificada como de pesado")
        
        if weighing_activities:
            weighing_activities_by_code[code] = {
                "code": code,
                "weighing_activities": weighing_activities,
                "total_weighing_activities": len(weighing_activities),
                "found": True
            }
            print(f"[DEBUG] filter_weighing_activities: Encontradas {len(weighing_activities)} actividades de pesado para código '{code}'")
        else:
            print(f"[DEBUG] filter_weighing_activities: No se encontraron actividades de pesado para código '{code}'")
    
    result = {
        "weighing_activities_by_code": weighing_activities_by_code,
        "total_codes_with_weighing": len(weighing_activities_by_code),
        "codes_with_weighing": list(weighing_activities_by_code.keys())
    }
    print(f"[DEBUG] filter_weighing_activities: Filtrado completado. {len(weighing_activities_by_code)} códigos tienen actividades de pesado")
    return result

def get_weighing_activities_for_orders(extracted_orders: list, db) -> dict:
    """
    Obtiene las actividades de pesado para todas las órdenes extraídas.
    
    Args:
        extracted_orders: Lista de órdenes extraídas (con lote, quantity, code)
        db: Sesión de base de datos
        
    Returns:
        Diccionario con todas las actividades y las de pesado filtradas
    """
    print(f"[DEBUG] get_weighing_activities_for_orders: Iniciando búsqueda de actividades de pesado")
    
    # Primero obtener todas las actividades
    all_activities = get_activities_for_extracted_orders(extracted_orders, db)
    
    # Luego filtrar solo las de pesado
    weighing_activities = filter_weighing_activities(all_activities)
    
    result = {
        "all_activities": all_activities,
        "weighing_activities": weighing_activities,
        "total_orders_processed": len(extracted_orders)
    }
    
    print(f"[DEBUG] get_weighing_activities_for_orders: Procesamiento completado")
    return result

def get_activity_details_by_code_and_activity(code: str, activity: str, db) -> dict:
    """
    Obtiene los datos detallados de una actividad específica basándose en el código y la actividad.
    
    Args:
        code: Código del producto
        activity: Nombre de la actividad
        db: Sesión de base de datos
        
    Returns:
        Diccionario con los datos detallados de la actividad
    """
    from app.models.code import Code
    
    print(f"[DEBUG] get_activity_details_by_code_and_activity: Buscando código '{code}' y actividad '{activity}'")
    
    code_obj = db.query(Code).filter(Code.code == code, Code.activity == activity).first()
    
    if not code_obj:
        print(f"[DEBUG] get_activity_details_by_code_and_activity: No se encontró código '{code}' con actividad '{activity}'")
        return {
            "success": False,
            "code": code,
            "activity": activity,
            "activity_details": None,
            "message": f"No se encontró código '{code}' con actividad '{activity}'"
        }
    
    # Obtener todos los campos solicitados
    activity_details = {
        "id": str(code_obj.id),
        "code": code_obj.code,
        "activity": code_obj.activity,
        "specification": code_obj.description,  # Usar description como specification
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
    
    print(f"[DEBUG] get_activity_details_by_code_and_activity: Encontrados datos para código '{code}' y actividad '{activity}'")
    print(f"[DEBUG] get_activity_details_by_code_and_activity: Datos - {activity_details}")
    
    return {
        "success": True,
        "code": code,
        "activity": activity,
        "activity_details": activity_details,
        "message": f"Datos obtenidos exitosamente para código '{code}' y actividad '{activity}'"
    }

def get_weighing_activities_with_details(extracted_orders: list, db) -> dict:
    """
    Obtiene las actividades de pesado para todas las órdenes extraídas y sus detalles específicos.
    
    Args:
        extracted_orders: Lista de órdenes extraídas (con lote, quantity, code)
        db: Sesión de base de datos
        
    Returns:
        Diccionario con todas las actividades, las de pesado filtradas y sus detalles
    """
    print(f"[DEBUG] get_weighing_activities_with_details: Iniciando búsqueda de actividades de pesado con detalles")
    
    # Primero obtener todas las actividades y las de pesado
    weighing_activities_data = get_weighing_activities_for_orders(extracted_orders, db)
    
    # Obtener detalles específicos para cada actividad de pesado
    weighing_activities_with_details = {}
    weighing_activities = weighing_activities_data.get("weighing_activities", {}).get("weighing_activities_by_code", {})
    
    for code, code_data in weighing_activities.items():
        print(f"[DEBUG] get_weighing_activities_with_details: Procesando código '{code}'")
        weighing_activities_list = code_data.get("weighing_activities", [])
        activities_with_details = []
        
        for activity_data in weighing_activities_list:
            activity_name = activity_data.get("activity")
            if activity_name:
                print(f"[DEBUG] get_weighing_activities_with_details: Obteniendo detalles para actividad '{activity_name}'")
                activity_details = get_activity_details_by_code_and_activity(code, activity_name, db)
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
    
    result = {
        "all_activities": weighing_activities_data.get("all_activities"),
        "weighing_activities": weighing_activities_data.get("weighing_activities"),
        "weighing_activities_with_details": {
            "weighing_activities_with_details_by_code": weighing_activities_with_details,
            "total_codes_with_weighing_details": len(weighing_activities_with_details),
            "codes_with_weighing_details": list(weighing_activities_with_details.keys())
        },
        "total_orders_processed": len(extracted_orders)
    }
    
    print(f"[DEBUG] get_weighing_activities_with_details: Procesamiento completado")
    return result

def calculate_minutes_from_performance_and_quantity(performance: float, quantity: int) -> int:
    """
    Calcula los minutos multiplicando performance (en horas) con la cantidad de la orden y convirtiendo a minutos.
    
    Args:
        performance: Rendimiento de la actividad en horas
        quantity: Cantidad de la orden
        
    Returns:
        Minutos calculados (entero)
    """
    print(f"[DEBUG] calculate_minutes_from_performance_and_quantity: Calculando minutos")
    print(f"[DEBUG] calculate_minutes_from_performance_and_quantity: performance={performance} horas, quantity={quantity}")
    
    if performance is None or quantity is None:
        print(f"[DEBUG] calculate_minutes_from_performance_and_quantity: Valores nulos detectados")
        return 0
    
    # Calcular horas: performance * quantity
    hours = performance * quantity
    print(f"[DEBUG] calculate_minutes_from_performance_and_quantity: Horas calculadas - {performance} * {quantity} = {hours} horas")
    
    # Convertir horas a minutos
    minutes = hours * 60
    minutes_int = int(minutes)
    
    # Aplicar ceiling (redondeo hacia arriba)
    import math
    minutes_ceiling = math.ceil(minutes)
    
    print(f"[DEBUG] calculate_minutes_from_performance_and_quantity: Conversión a minutos - {hours} horas * 60 = {minutes} -> {minutes_int} minutos")
    print(f"[DEBUG] calculate_minutes_from_performance_and_quantity: Aplicando ceiling - {minutes} -> {minutes_ceiling} minutos")
    
    return minutes_ceiling

def get_activity_details_with_minutes_calculation(code: str, activity: str, order_quantity: int, db) -> dict:
    """
    Obtiene los datos detallados de una actividad específica y calcula los minutos
    basándose en el performance y la cantidad de la orden.
    
    Args:
        code: Código del producto
        activity: Nombre de la actividad
        order_quantity: Cantidad de la orden
        db: Sesión de base de datos
        
    Returns:
        Diccionario con los datos detallados de la actividad y minutos calculados
    """
    print(f"[DEBUG] get_activity_details_with_minutes_calculation: Obteniendo detalles con cálculo de minutos")
    print(f"[DEBUG] get_activity_details_with_minutes_calculation: código='{code}', actividad='{activity}', cantidad={order_quantity}")
    
    # Obtener detalles de la actividad
    activity_details_result = get_activity_details_by_code_and_activity(code, activity, db)
    
    if not activity_details_result.get("success", False):
        print(f"[DEBUG] get_activity_details_with_minutes_calculation: No se pudieron obtener detalles de la actividad")
        return activity_details_result
    
    activity_details = activity_details_result.get("activity_details", {})
    performance = activity_details.get("performance")
    
    # Calcular minutos
    calculated_minutes = calculate_minutes_from_performance_and_quantity(performance, order_quantity)
    
    # Calcular horas para mostrar en la fórmula
    hours_calculation = performance * order_quantity
    
    # Agregar minutos calculados al resultado
    result = {
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
    
    print(f"[DEBUG] get_activity_details_with_minutes_calculation: Resultado final - {result}")
    return result

def get_weighing_activities_with_minutes_calculation(extracted_orders: list, db) -> dict:
    """
    Obtiene las actividades de pesado para todas las órdenes extraídas y calcula los minutos
    para cada actividad basándose en el performance y la cantidad de la orden.
    
    Args:
        extracted_orders: Lista de órdenes extraídas (con lote, quantity, code)
        db: Sesión de base de datos
        
    Returns:
        Diccionario con todas las actividades, las de pesado filtradas y minutos calculados
    """
    print(f"[DEBUG] get_weighing_activities_with_minutes_calculation: Iniciando cálculo de minutos para actividades de pesado")
    
    # Primero obtener todas las actividades y las de pesado con detalles
    weighing_activities_with_details_data = get_weighing_activities_with_details(extracted_orders, db)
    
    # Calcular minutos para cada actividad de pesado
    weighing_activities_with_minutes = {}
    weighing_activities_with_details = weighing_activities_with_details_data.get("weighing_activities_with_details", {}).get("weighing_activities_with_details_by_code", {})
    
    for code, code_data in weighing_activities_with_details.items():
        print(f"[DEBUG] get_weighing_activities_with_minutes_calculation: Procesando código '{code}'")
        weighing_activities_list = code_data.get("weighing_activities_with_details", [])
        activities_with_minutes = []
        
        for activity_item in weighing_activities_list:
            activity_data = activity_item.get("activity_data", {})
            activity_details = activity_item.get("activity_details", {})
            activity_name = activity_data.get("activity")
            
            if activity_name and activity_details.get("success", False):
                # Buscar la cantidad de la orden correspondiente
                order_quantity = None
                for order in extracted_orders:
                    if order.get("code") == code:
                        order_quantity = order.get("quantity")
                        break
                
                if order_quantity is not None:
                    print(f"[DEBUG] get_weighing_activities_with_minutes_calculation: Calculando minutos para actividad '{activity_name}' con cantidad {order_quantity}")
                    
                    # Calcular minutos
                    performance = activity_details.get("activity_details", {}).get("performance")
                    calculated_minutes = calculate_minutes_from_performance_and_quantity(performance, order_quantity)
                    
                    # Calcular horas para mostrar en la fórmula
                    hours_calculation = performance * order_quantity
                    
                    activities_with_minutes.append({
                        "activity_data": activity_data,
                        "activity_details": activity_details,
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
    
    result = {
        "all_activities": weighing_activities_with_details_data.get("all_activities"),
        "weighing_activities": weighing_activities_with_details_data.get("weighing_activities"),
        "weighing_activities_with_details": weighing_activities_with_details_data.get("weighing_activities_with_details"),
        "weighing_activities_with_minutes": {
            "weighing_activities_with_minutes_by_code": weighing_activities_with_minutes,
            "total_codes_with_weighing_minutes": len(weighing_activities_with_minutes),
            "codes_with_weighing_minutes": list(weighing_activities_with_minutes.keys())
        },
        "total_orders_processed": len(extracted_orders)
    }
    
    print(f"[DEBUG] get_weighing_activities_with_minutes_calculation: Procesamiento completado")
    return result


def get_most_suitable_weighing_team(db) -> dict:
    """
    Obtiene el equipo más idóneo para actividades de pesado.
    
    Args:
        db: Sesión de base de datos
        
    Returns:
        Diccionario con información del equipo más idóneo para pesado
    """
    print(f"[DEBUG] get_most_suitable_weighing_team: Buscando equipo más idóneo para pesado")
    
    # Buscar equipos que contengan "pesado" en el nombre
    weighing_teams = db.query(Team).filter(Team.name.ilike('%pesado%')).all()
    
    print(f"[DEBUG] get_most_suitable_weighing_team: Equipos encontrados con 'pesado' en el nombre: {len(weighing_teams)}")
    
    if not weighing_teams:
        print(f"[DEBUG] get_most_suitable_weighing_team: No se encontraron equipos de pesado")
        return {
            "success": False,
            "message": "No se encontraron equipos de pesado en la base de datos",
            "weighing_teams": [],
            "most_suitable_team": None
        }
    
    # Mostrar todos los equipos encontrados
    for i, team in enumerate(weighing_teams):
        print(f"[DEBUG] get_most_suitable_weighing_team: Equipo {i+1} - ID: {team.id}, Nombre: '{team.name}'")
    
    # Lógica para determinar el equipo más idóneo
    # Prioridad: 1. "pesado principal", 2. "pesado 1", 3. primer equipo con "pesado"
    most_suitable_team = None
    
    # Buscar "pesado principal"
    for team in weighing_teams:
        if "principal" in team.name.lower():
            most_suitable_team = team
            print(f"[DEBUG] get_most_suitable_weighing_team: Encontrado equipo principal - ID: {team.id}, Nombre: '{team.name}'")
            break
    
    # Si no hay principal, buscar "pesado 1"
    if not most_suitable_team:
        for team in weighing_teams:
            if "pesado 1" in team.name.lower() or "pesado1" in team.name.lower():
                most_suitable_team = team
                print(f"[DEBUG] get_most_suitable_weighing_team: Encontrado equipo pesado 1 - ID: {team.id}, Nombre: '{team.name}'")
                break
    
    # Si no hay ninguno específico, tomar el primero
    if not most_suitable_team and weighing_teams:
        most_suitable_team = weighing_teams[0]
        print(f"[DEBUG] get_most_suitable_weighing_team: Usando primer equipo disponible - ID: {most_suitable_team.id}, Nombre: '{most_suitable_team.name}'")
    
    if most_suitable_team:
        result = {
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
        
        print(f"[DEBUG] get_most_suitable_weighing_team: Equipo seleccionado - ID: {most_suitable_team.id}, Nombre: '{most_suitable_team.name}'")
        print(f"[DEBUG] get_most_suitable_weighing_team: Total de equipos de pesado: {len(weighing_teams)}")
        
        return result
    else:
        print(f"[DEBUG] get_most_suitable_weighing_team: No se pudo determinar el equipo más idóneo")
        return {
            "success": False,
            "message": "No se pudo determinar el equipo más idóneo para pesado",
            "weighing_teams": [],
            "most_suitable_team": None
        }


def get_most_suitable_weighing_team_with_available_programmings(db) -> dict:
    """
    Obtiene el equipo más idóneo para actividades de pesado y sus programaciones disponibles.
    Si no hay programaciones disponibles, crea una nueva programación.
    
    Args:
        db: Sesión de base de datos
        
    Returns:
        Diccionario con información del equipo más idóneo para pesado y sus programaciones disponibles
    """
    print(f"[DEBUG] get_most_suitable_weighing_team_with_available_programmings: Iniciando búsqueda de equipo y programaciones")
    
    # Primero obtener el equipo más idóneo para pesado
    team_result = get_most_suitable_weighing_team(db)
    
    if not team_result.get("success", False):
        print(f"[DEBUG] get_most_suitable_weighing_team_with_available_programmings: No se pudo obtener equipo idóneo")
        return {
            "success": False,
            "message": "No se pudo obtener equipo idóneo para pesado",
            "team_data": team_result,
            "available_programmings": []
        }
    
    most_suitable_team = team_result.get("most_suitable_team")
    team_id = most_suitable_team.get("id")
    
    print(f"[DEBUG] get_most_suitable_weighing_team_with_available_programmings: Equipo obtenido - ID: {team_id}, Nombre: {most_suitable_team.get('name')}")
    
    # Obtener programaciones disponibles para el equipo
    from datetime import date, timedelta
    from app.models.programming import Programming, ProgrammingStatus
    
    current_date = date.today()
    
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
    
    print(f"[DEBUG] get_most_suitable_weighing_team_with_available_programmings: Programaciones disponibles encontradas: {len(available_programmings)}")
    
    # Si no hay programaciones disponibles, crear una nueva
    if len(available_programmings) == 0:
        print(f"[DEBUG] get_most_suitable_weighing_team_with_available_programmings: No hay programaciones disponibles, creando nueva programación")
        
        # Obtener la última programación del equipo (sin importar el estado)
        last_programming = (
            db.query(Programming)
            .filter(Programming.team_id == team_id)
            .order_by(Programming.date.desc())
            .first()
        )
        
        if last_programming:
            # Calcular la fecha para la nueva programación (un día después de la última)
            new_date = last_programming.date + timedelta(days=1)
            print(f"[DEBUG] get_most_suitable_weighing_team_with_available_programmings: Última programación encontrada - Fecha: {last_programming.date}")
        else:
            # Si no hay programaciones previas, usar mañana como fecha base
            new_date = current_date + timedelta(days=1)
            print(f"[DEBUG] get_most_suitable_weighing_team_with_available_programmings: No hay programaciones previas, usando mañana como fecha base")
        
        # Evitar domingos (día 6, donde lunes=0, domingo=6)
        while new_date.weekday() == 6:  # 6 = domingo
            new_date += timedelta(days=1)
            print(f"[DEBUG] get_most_suitable_weighing_team_with_available_programmings: Evitando domingo, nueva fecha: {new_date}")
        
        # Verificar que no exista ya una programación para esa fecha
        existing_programming = (
            db.query(Programming)
            .filter(Programming.team_id == team_id, Programming.date == new_date)
            .first()
        )
        
        if existing_programming:
            print(f"[DEBUG] get_most_suitable_weighing_team_with_available_programmings: Ya existe programación para {new_date}, buscando siguiente fecha disponible")
            # Buscar la siguiente fecha disponible
            while existing_programming:
                new_date += timedelta(days=1)
                # Evitar domingos
                while new_date.weekday() == 6:
                    new_date += timedelta(days=1)
                existing_programming = (
                    db.query(Programming)
                    .filter(Programming.team_id == team_id, Programming.date == new_date)
                    .first()
                )
        
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
            print(f"[DEBUG] get_most_suitable_weighing_team_with_available_programmings: Nueva programación creada - ID: {new_programming.id}, Fecha: {new_date}")
            
            # Agregar la nueva programación a la lista
            programming_info = {
                "id": str(new_programming.id),
                "date": new_programming.date.isoformat(),
                "status": new_programming.status.value if new_programming.status else "available",
                "team_id": str(new_programming.team_id),
                "total_tasks": 0,
                "is_newly_created": True
            }
            available_programmings = [new_programming]
            programming_data = [programming_info]
            
        except Exception as e:
            print(f"[DEBUG] get_most_suitable_weighing_team_with_available_programmings: Error al crear nueva programación: {e}")
            db.rollback()
            programming_data = []
    else:
        # Preparar datos de programaciones disponibles existentes
        programming_data = []
        for programming in available_programmings:
            programming_info = {
                "id": str(programming.id),
                "date": programming.date.isoformat(),
                "status": programming.status.value if programming.status else "available",
                "team_id": str(programming.team_id),
                "total_tasks": len(programming.programming_tasks) if programming.programming_tasks else 0,
                "is_newly_created": False
            }
            programming_data.append(programming_info)
            print(f"[DEBUG] get_most_suitable_weighing_team_with_available_programmings: Programación - ID: {programming_info['id']}, Fecha: {programming_info['date']}, Tareas: {programming_info['total_tasks']}")
    
    result = {
        "success": True,
        "message": f"Equipo idóneo y programaciones obtenidas exitosamente",
        "team_data": team_result,
        "available_programmings": {
            "success": True,
            "message": "Programaciones disponibles obtenidas exitosamente",
            "team_id": team_id,
            "team_name": most_suitable_team.get("name"),
            "programmings": programming_data,
            "total_available_programmings": len(programming_data),
            "current_date": current_date.isoformat()
        }
    }
    
    print(f"[DEBUG] get_most_suitable_weighing_team_with_available_programmings: Procesamiento completado - {len(programming_data)} programaciones disponibles")
    return result


def verify_programming_time_limit_simple(programmings: list, task_minutes: int, db, order_data: dict = None, activity_details: dict = None) -> dict:
    """
    Verifica que al agregar una tarea a una programación no se exceda el límite de tiempo (17:40) más de 5 minutos.
    Versión simplificada sin logs de debug.
    """
    from app.models.programming import ProgrammingTask
    from app.models.task import Task
    from app.models.team import Team
    from datetime import datetime, timedelta, time
    
    time_limit = time(17, 40)  # 17:40
    tolerance_minutes = 5
    max_allowed_minutes = time_limit.hour * 60 + time_limit.minute + tolerance_minutes
    
    for programming in programmings:
        programming_id = programming.get("id")
        programming_date = programming.get("date")
        
        # Obtener la programación completa de la base de datos
        programming_obj = db.query(Programming).filter(Programming.id == programming_id).first()
        if not programming_obj:
            continue
        
        # Obtener las tareas de la programación
        programming_tasks = db.query(ProgrammingTask).filter(ProgrammingTask.programming_id == programming_id).all()
        
        # Determinar el tiempo actual de la programación
        if not programming_tasks:
            # Programación vacía - crear tarea de preparación automática
            # Crear la tarea de preparación con tiempo fijo
            # Usar la fecha de la programación para mantener consistencia
            programming_date_obj = datetime.strptime(programming_date, "%Y-%m-%d")
            preparation_start_time = programming_date_obj.replace(hour=7, minute=0, second=0, microsecond=0)
            preparation_end_time = programming_date_obj.replace(hour=7, minute=10, second=0, microsecond=0)
            
            preparation_task_obj = Task(
                description="REUNION Y PREPARACION DE AREA",
                minutes=10,
                start_time=preparation_start_time,
                end_time=preparation_end_time
            )
            
            preparation_task = ProgrammingTask(
                programming_id=programming_id,
                task_id=preparation_task_obj.id,
                order=1
            )
            
            try:
                db.add(preparation_task_obj)
                db.flush()
                preparation_task.task_id = preparation_task_obj.id
                db.add(preparation_task)
                db.commit()
                db.refresh(preparation_task_obj)
                db.refresh(preparation_task)
                
                current_end_time = preparation_end_time
                current_end_minutes = current_end_time.hour * 60 + current_end_time.minute
                
            except Exception as e:
                db.rollback()
                current_end_time = preparation_end_time
                current_end_minutes = current_end_time.hour * 60 + current_end_time.minute
        else:
            # Ordenar tareas por end_time y obtener la última
            sorted_tasks = sorted(programming_tasks, key=lambda x: x.end_time if x.end_time else time(0, 0))
            last_task = sorted_tasks[-1]
            current_end_time = last_task.end_time
            
            if not current_end_time:
                current_end_time = time(7, 0)
            
            current_end_minutes = current_end_time.hour * 60 + current_end_time.minute
        
        # Calcular el tiempo final si se agrega la nueva tarea
        final_minutes = current_end_minutes + task_minutes
        final_time = time(final_minutes // 60, final_minutes % 60)
        
        # Verificar si se excede el límite
        if final_minutes <= max_allowed_minutes:
            # Obtener información del equipo
            team_obj = db.query(Team).filter(Team.id == programming_obj.team_id).first()
            team_name = team_obj.name if team_obj else "Equipo desconocido"
            
            result = {
                "success": True,
                "message": f"Programación seleccionada que cumple con límite de tiempo",
                "selected_programming": {
                    "id": programming_id,
                    "date": programming_date,
                    "team_id": str(programming_obj.team_id),
                    "team_name": team_name,
                    "current_end_time": current_end_time.isoformat(),
                    "task_minutes": task_minutes,
                    "final_time": final_time.isoformat(),
                    "time_limit": time_limit.isoformat(),
                    "tolerance_minutes": tolerance_minutes
                },
                "verification_details": {
                    "current_end_minutes": current_end_minutes,
                    "final_minutes": final_minutes,
                    "max_allowed_minutes": max_allowed_minutes,
                    "within_limit": True
                }
            }
            
            # Crear la tarea de la orden si se proporcionaron los datos
            if order_data and activity_details:
                try:
                    # Calcular start_time y end_time para la nueva tarea
                    # current_end_time ya es un datetime (viene de preparation_end_time)
                    task_start_time = current_end_time
                    
                    # Calcular end_time sumando los minutos
                    task_end_time = task_start_time + timedelta(minutes=task_minutes)
                    
                    # Obtener el UUID del código específico para la actividad PESADO
                    from app.models.code import Code
                    code_obj = db.query(Code).filter(
                        Code.code == order_data.get('code'),
                        Code.activity == activity_details.get('activity')
                    ).first()
                    code_id = code_obj.id if code_obj else None
                    
                    print(f"[DEBUG] Task Creation - Code UUID: {code_id}")
                    print(f"[DEBUG] Task Creation - Code Object: {code_obj.code if code_obj else 'None'}")
                    print(f"[DEBUG] Task Creation - Code Activity: {code_obj.activity if code_obj else 'None'}")
                    print(f"[DEBUG] Task Creation - Code Type: {code_obj.type if code_obj else 'None'}")
                    print(f"[DEBUG] Task Creation - Activity Details: {activity_details}")
                    
                    # Crear la tarea de la orden
                    order_task_obj = Task(
                        code_id=code_id,  # Usar el UUID del código
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
                    # Si se creó una tarea de preparación, ahora hay una tarea más
                    if not programming_tasks:  # Si la programación estaba vacía
                        new_task_order = 2  # La preparación es orden 1, esta será orden 2
                    else:
                        existing_tasks_count = len(programming_tasks)
                        new_task_order = existing_tasks_count + 1
                    
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
                    
                    # Agregar información de la tarea creada al resultado
                    result["order_task_created"] = {
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
                    
                except Exception as e:
                    db.rollback()
            
            return result
        else:
            continue
    
    # Si ninguna programación cumple con el límite
    return {
        "success": False,
        "message": "Ninguna programación cumple con el límite de tiempo",
        "selected_programming": None
    }


def get_most_suitable_weighing_team_with_time_verification(db, task_minutes: int) -> dict:
    """
    Obtiene el equipo más idóneo para pesado, sus programaciones disponibles y verifica el límite de tiempo.
    
    Args:
        db: Sesión de base de datos
        task_minutes: Minutos de la tarea a agregar
        
    Returns:
        Diccionario con equipo, programaciones y verificación de tiempo
    """
    print(f"[DEBUG] get_most_suitable_weighing_team_with_time_verification: Iniciando búsqueda con verificación de tiempo")
    print(f"[DEBUG] get_most_suitable_weighing_team_with_time_verification: Minutos de la tarea: {task_minutes}")
    
    # Primero obtener equipo y programaciones
    team_and_programmings_result = get_most_suitable_weighing_team_with_available_programmings(db)
    
    if not team_and_programmings_result.get("success", False):
        print(f"[DEBUG] get_most_suitable_weighing_team_with_time_verification: No se pudo obtener equipo y programaciones")
        return {
            "success": False,
            "message": "No se pudo obtener equipo idóneo y programaciones",
            "team_data": None,
            "available_programmings": None,
            "time_verification": None
        }
    
    team_data = team_and_programmings_result.get("team_data")
    available_programmings = team_and_programmings_result.get("available_programmings")
    
    if not available_programmings or not available_programmings.get("programmings"):
        print(f"[DEBUG] get_most_suitable_weighing_team_with_time_verification: No hay programaciones disponibles")
        return {
            "success": False,
            "message": "No hay programaciones disponibles para verificar",
            "team_data": team_data,
            "available_programmings": available_programmings,
            "time_verification": None
        }
    
    # Verificar límite de tiempo
    time_verification = verify_programming_time_limit_simple(
        available_programmings["programmings"], 
        task_minutes, 
        db
    )
    
    result = {
        "success": True,
        "message": "Equipo idóneo, programaciones y verificación de tiempo obtenidos exitosamente",
        "team_data": team_data,
        "available_programmings": available_programmings,
        "time_verification": time_verification
    }
    
    print(f"[DEBUG] get_most_suitable_weighing_team_with_time_verification: Procesamiento completado")
    return result

def create_weighing_task_for_order(extracted_orders: list, db) -> dict:
    """
    Función unificada que maneja todo el proceso de creación de tareas de pesado cuando se agrega una orden.
    
    Args:
        extracted_orders: Lista de órdenes extraídas con lote, quantity y code
        db: Sesión de base de datos
    
    Returns:
        dict: Resultado del proceso con información de la tarea creada
    """
    try:
        # Obtener actividades de pesado con minutos calculados
        weighing_activities_with_minutes_data = get_weighing_activities_with_minutes_calculation(extracted_orders, db)
        
        # Obtener equipo con programaciones disponibles
        team_with_programmings_data = get_most_suitable_weighing_team_with_available_programmings(db)
        
        # Verificar si hay datos válidos para procesar
        if not weighing_activities_with_minutes_data.get("weighing_activities_with_minutes", {}).get("weighing_activities_with_minutes_by_code"):
            return {
                "success": False,
                "message": "No se encontraron actividades de pesado para las órdenes",
                "task_created": False
            }
        
        if not team_with_programmings_data.get("available_programmings", {}).get("programmings"):
            return {
                "success": False,
                "message": "No se encontraron programaciones disponibles para el equipo de pesado",
                "task_created": False
            }
        
        # Obtener los datos de la primera orden y actividad
        order_data = extracted_orders[0] if extracted_orders else None
        if not order_data:
            return {
                "success": False,
                "message": "No hay datos de orden para procesar",
                "task_created": False
            }
        
        # Obtener la actividad de pesado específica con minutos calculados
        pesado_activity = None
        for code_data in weighing_activities_with_minutes_data["weighing_activities_with_minutes"]["weighing_activities_with_minutes_by_code"].values():
            if code_data.get("weighing_activities_with_minutes"):
                # Buscar específicamente la actividad "PESADO"
                for activity in code_data["weighing_activities_with_minutes"]:
                    activity_name = activity.get("activity_details", {}).get("activity_details", {}).get("activity", "")
                    if activity_name and "PESADO" in activity_name.upper():
                        pesado_activity = activity
                        break
                # Si no se encuentra "PESADO", usar la primera actividad disponible
                if not pesado_activity:
                    pesado_activity = code_data["weighing_activities_with_minutes"][0]
                break
        
        if not pesado_activity:
            return {
                "success": False,
                "message": "No se encontró actividad de pesado válida",
                "task_created": False
            }
        
        task_minutes = pesado_activity.get("minutes_calculation", {}).get("calculated_minutes", 0)
        activity_details = pesado_activity.get("activity_details", {}).get("activity_details", {})
        
        if task_minutes <= 0:
            return {
                "success": False,
                "message": "Los minutos calculados no son válidos",
                "task_created": False
            }
        
        # Verificar límite de tiempo y crear tarea
        time_verification_data = verify_programming_time_limit_simple(
            team_with_programmings_data["available_programmings"]["programmings"],
            task_minutes,
            db,
            order_data,
            activity_details
        )
        
        if not time_verification_data.get("success"):
            return {
                "success": False,
                "message": "No se pudo encontrar una programación adecuada para la tarea",
                "task_created": False
            }
        
        # Verificar si se creó la tarea
        if time_verification_data.get("order_task_created"):
            return {
                "success": True,
                "message": "Tarea de pesado creada exitosamente",
                "task_created": True,
                "selected_programming": time_verification_data.get("selected_programming"),
                "order_task": time_verification_data.get("order_task_created"),
                "team_data": team_with_programmings_data.get("most_suitable_team"),
                "weighing_activities_data": weighing_activities_with_minutes_data
            }
        else:
            return {
                "success": True,
                "message": "Programación seleccionada pero no se pudo crear la tarea",
                "task_created": False,
                "selected_programming": time_verification_data.get("selected_programming"),
                "team_data": team_with_programmings_data.get("most_suitable_team"),
                "weighing_activities_data": weighing_activities_with_minutes_data
            }
            
    except Exception as e:
        return {
            "success": False,
            "message": f"Error durante la creación de tarea de pesado: {str(e)}",
            "task_created": False
        }
    