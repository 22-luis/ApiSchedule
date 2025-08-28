"""
Ejemplos de uso del servicio de empaque
"""

from app.services.factory import TaskServiceFactory
from app.services.config import ServiceType
from app.core.enums import PackagingActivities, PackagingTeams


def example_packaging_service_usage():
    """Ejemplo básico de uso del servicio de empaque"""
    print("🚀 Ejemplo de uso del servicio de empaque")
    print("=" * 50)
    
    # Crear el servicio de empaque
    packaging_service = TaskServiceFactory.create_packaging_service()
    
    print(f"✅ Servicio creado: {type(packaging_service).__name__}")
    print(f"   - Límite de tiempo: {packaging_service.time_limit}")
    print(f"   - Tolerancia: {packaging_service.tolerance_minutes} minutos")
    
    # Mostrar información de configuración
    config = packaging_service.get_service_config()
    print(f"\n⚙️ Configuración del servicio:")
    print(f"   - Descripción: {config.get('description', 'N/A')}")
    print(f"   - Palabras clave: {config.get('activity_keywords', [])}")
    print(f"   - Prioridades de equipos: {config.get('team_priorities', [])}")
    
    # Mostrar enumeraciones disponibles
    print(f"\n📋 Enumeraciones disponibles:")
    print("   Actividades de empaque:")
    for activity in PackagingActivities:
        print(f"     - {activity.name}: {activity.value}")
    
    print("   Equipos de empaque:")
    for team in PackagingTeams:
        print(f"     - {team.name}: {team.value}")
    
    print("\n✅ Ejemplo completado exitosamente")


def example_complete_workflow_with_packaging():
    """Ejemplo de flujo completo incluyendo empaque"""
    print("🔄 Ejemplo de flujo completo con empaque")
    print("=" * 50)
    
    # Crear servicios para diferentes tipos de tareas
    weighing_service = TaskServiceFactory.create_weighing_service()
    fabrication_service = TaskServiceFactory.create_fabrication_service()
    packaging_service = TaskServiceFactory.create_packaging_service()
    
    print("✅ Servicios creados:")
    print(f"   - Pesaje: {type(weighing_service).__name__}")
    print(f"   - Fabricación: {type(fabrication_service).__name__}")
    print(f"   - Empaque: {type(packaging_service).__name__}")
    
    # Mostrar configuración de cada servicio
    print(f"\n⚙️ Configuraciones:")
    print(f"   - Pesaje: {weighing_service.time_limit}")
    print(f"   - Fabricación: {fabrication_service.time_limit}")
    print(f"   - Empaque: {packaging_service.time_limit}")
    
    print("\n✅ Flujo completo demostrado")


def example_generic_service_usage():
    """Ejemplo de uso genérico del factory"""
    print("🏭 Ejemplo de uso genérico del factory")
    print("=" * 50)
    
    # Listar servicios disponibles
    available_services = TaskServiceFactory.get_available_services()
    print(f"📋 Servicios disponibles: {available_services}")
    
    # Crear servicios dinámicamente
    for service_type in available_services:
        service = TaskServiceFactory.create_service(service_type)
        print(f"✅ {service_type}: {type(service).__name__}")
        
        # Si es el servicio de empaque, mostrar información específica
        if service_type == ServiceType.PACKAGING:
            print(f"   - Límite de tiempo: {service.time_limit}")
            print(f"   - Tolerancia: {service.tolerance_minutes} minutos")
    
    print("\n✅ Uso genérico completado")


def api_endpoint_example_with_packaging():
    """Ejemplo de endpoint API que maneja empaque"""
    print("🌐 Ejemplo de endpoint API con empaque")
    print("=" * 50)
    
    def create_tasks_endpoint(service_type: str, orders_data: list, db):
        """Endpoint simulado para crear tareas"""
        try:
            # Crear el servicio apropiado
            service = TaskServiceFactory.create_service(service_type)
            
            if service_type == ServiceType.PACKAGING:
                # Para empaque, usar el método específico
                result = service.create_packaging_tasks_for_orders(orders_data, db)
        else:
                # Para otros servicios, usar el método genérico
                result = service.create_tasks_for_orders(orders_data, db)
        
        return {
            "success": True,
                "service_type": service_type,
                "result": result
        }
        
    except Exception as e:
        return {
            "success": False,
                "error": str(e),
            "service_type": service_type
        }

    # Simular llamadas al endpoint
    print("📡 Simulando llamadas al endpoint:")
    
    # Ejemplo con empaque
    print("\n1. Creando tareas de empaque...")
    packaging_result = create_tasks_endpoint(
        ServiceType.PACKAGING, 
        [{"lote": "TEST001", "quantity": 100}], 
        None
    )
    print(f"   Resultado: {packaging_result['success']}")
    
    # Ejemplo con pesaje
    print("\n2. Creando tareas de pesaje...")
    weighing_result = create_tasks_endpoint(
        ServiceType.WEIGHING, 
        [{"lote": "TEST002", "quantity": 50}], 
        None
    )
    print(f"   Resultado: {weighing_result['success']}")
    
    print("\n✅ Ejemplo de endpoint completado")


if __name__ == "__main__":
    print("🚀 Ejecutando ejemplos de uso del servicio de empaque")
    print("=" * 60)
    
    # Ejecutar todos los ejemplos
    example_packaging_service_usage()
    print("\n" + "=" * 60)
    
    example_complete_workflow_with_packaging()
    print("\n" + "=" * 60)
    
    example_generic_service_usage()
    print("\n" + "=" * 60)
    
    api_endpoint_example_with_packaging()
    print("\n" + "=" * 60)
    
    print("🎉 Todos los ejemplos completados exitosamente")
