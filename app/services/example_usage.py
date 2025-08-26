"""
Ejemplo de uso de los servicios refactorizados.
Demuestra cómo usar los nuevos servicios de tareas.
"""

from typing import List, Dict, Any
from sqlalchemy.orm import Session

from app.services.factory import TaskServiceFactory
from app.services.config import ServiceType


def example_weighing_service_usage(db: Session, orders: List) -> Dict[str, Any]:
    """
    Ejemplo de uso del servicio de pesado refactorizado.
    
    Args:
        db: Sesión de base de datos
        orders: Lista de órdenes de la base de datos
        
    Returns:
        Resultado del procesamiento de tareas de pesado
    """
    # Crear instancia del servicio usando el factory
    weighing_service = TaskServiceFactory.create_weighing_service()
    
    # Extraer datos de las órdenes
    extracted_orders = weighing_service.extract_order_data(orders)
    
    # Crear tareas de pesado
    result = weighing_service.create_weighing_tasks_for_orders(extracted_orders, db)
    
    return result


def example_fabrication_service_usage(db: Session, orders: List) -> Dict[str, Any]:
    """
    Ejemplo de uso del servicio de fabricación refactorizado.
    
    Args:
        db: Sesión de base de datos
        orders: Lista de órdenes de la base de datos
        
    Returns:
        Resultado del procesamiento de tareas de fabricación
    """
    # Crear instancia del servicio usando el factory
    fabrication_service = TaskServiceFactory.create_fabrication_service()
    
    # Extraer datos de las órdenes
    extracted_orders = fabrication_service.extract_order_data(orders)
    
    # Crear tareas de fabricación
    result = fabrication_service.create_fabrication_tasks_for_orders(extracted_orders, db)
    
    return result


def example_generic_service_usage(db: Session, orders: List, service_type: ServiceType) -> Dict[str, Any]:
    """
    Ejemplo de uso genérico de cualquier servicio.
    
    Args:
        db: Sesión de base de datos
        orders: Lista de órdenes de la base de datos
        service_type: Tipo de servicio a usar
        
    Returns:
        Resultado del procesamiento de tareas
    """
    # Crear instancia del servicio usando el factory
    service = TaskServiceFactory.create_service(service_type)
    
    if not service:
        return {
            "success": False,
            "message": f"Servicio de tipo {service_type.value} no está disponible"
        }
    
    # Extraer datos de las órdenes
    extracted_orders = service.extract_order_data(orders)
    
    # Crear tareas según el tipo de servicio
    if service_type == ServiceType.WEIGHING:
        result = service.create_weighing_tasks_for_orders(extracted_orders, db)
    elif service_type == ServiceType.FABRICATION:
        result = service.create_fabrication_tasks_for_orders(extracted_orders, db)
    else:
        result = {
            "success": False,
            "message": f"Método de creación no implementado para {service_type.value}"
        }
    
    return result


def example_service_information() -> Dict[str, Any]:
    """
    Ejemplo de cómo obtener información sobre los servicios disponibles.
    
    Returns:
        Información de todos los servicios disponibles
    """
    available_services = TaskServiceFactory.get_available_services()
    services_info = {}
    
    for service_type in available_services:
        services_info[service_type.value] = TaskServiceFactory.get_service_info(service_type)
    
    return {
        "available_services": [service.value for service in available_services],
        "services_info": services_info
    }


def example_complete_workflow(db: Session, orders: List) -> Dict[str, Any]:
    """
    Ejemplo de flujo completo de trabajo usando ambos servicios.
    
    Args:
        db: Sesión de base de datos
        orders: Lista de órdenes de la base de datos
        
    Returns:
        Resultado completo del procesamiento
    """
    results = {}
    
    # Procesar tareas de pesado
    weighing_result = example_weighing_service_usage(db, orders)
    results["weighing"] = weighing_result
    
    # Procesar tareas de fabricación
    fabrication_result = example_fabrication_service_usage(db, orders)
    results["fabrication"] = fabrication_result
    
    # Resumen general
    total_tasks_created = (
        weighing_result.get("tasks_created", 0) + 
        fabrication_result.get("tasks_created", 0)
    )
    
    total_orders = len(orders)
    
    return {
        "success": True,
        "message": f"Procesamiento completo: {total_tasks_created} tareas creadas de {total_orders} órdenes",
        "total_tasks_created": total_tasks_created,
        "total_orders": total_orders,
        "results": results
    }


# Ejemplo de uso en un endpoint de API
def api_endpoint_example(db: Session, orders: List, service_type: str) -> Dict[str, Any]:
    """
    Ejemplo de cómo usar los servicios en un endpoint de API.
    
    Args:
        db: Sesión de base de datos
        orders: Lista de órdenes de la base de datos
        service_type: Tipo de servicio como string ("weighing", "fabrication")
        
    Returns:
        Respuesta del endpoint
    """
    try:
        # Convertir string a ServiceType
        if service_type == "weighing":
            service_type_enum = ServiceType.WEIGHING
        elif service_type == "fabrication":
            service_type_enum = ServiceType.FABRICATION
        else:
            return {
                "success": False,
                "message": f"Tipo de servicio '{service_type}' no válido. Opciones: weighing, fabrication"
            }
        
        # Procesar usando el servicio genérico
        result = example_generic_service_usage(db, orders, service_type_enum)
        
        return {
            "success": True,
            "data": result,
            "service_type": service_type
        }
        
    except Exception as e:
        return {
            "success": False,
            "message": f"Error en el procesamiento: {str(e)}",
            "service_type": service_type
        }
