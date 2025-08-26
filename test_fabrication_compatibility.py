"""
Script de prueba para verificar las funciones de compatibilidad del servicio de fabricación en task_config.py
"""
import sys
import os
from datetime import datetime, date

# Agregar el directorio raíz al path para importar los módulos
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy.orm import Session
from app.db.database import SessionLocal
from app.core.task_config import (
    get_fabrication_activities_by_code,
    get_fabrication_activities_for_orders,
    get_fabrication_activities_with_details,
    get_fabrication_activity_details_by_code_and_activity,
    get_fabrication_activity_details_with_minutes_calculation,
    get_fabrication_activities_with_minutes_calculation,
    calculate_fabrication_minutes_from_performance_and_quantity,
    get_most_suitable_fabrication_team,
    get_most_suitable_fabrication_team_with_available_programmings,
    verify_fabrication_programming_time_limit_simple,
    get_most_suitable_fabrication_team_with_time_verification,
    create_fabrication_task_for_order,
    create_fabrication_tasks_for_multiple_orders,
    get_fabrication_activity_for_order,
    update_fabrication_programming_list_after_task_creation,
    create_single_fabrication_task
)
from app.models.order import Order
from app.models.state import OrderStatus

def test_fabrication_compatibility_functions():
    """Prueba las funciones de compatibilidad del servicio de fabricación"""
    db = SessionLocal()
    
    try:
        print("🧪 Iniciando prueba de funciones de compatibilidad de fabricación...")
        
        # Crear datos de prueba
        test_orders = [
            {
                "lote": "TEST001",
                "quantity": 100,
                "code": "PROD-001"
            },
            {
                "lote": "TEST002", 
                "quantity": 50,
                "code": "PROD-002"
            }
        ]
        
        print(f"📋 Datos de prueba: {test_orders}")
        
        # 1. Probar get_fabrication_activities_by_code
        print("\n1️⃣ Probando get_fabrication_activities_by_code...")
        activities_by_code = get_fabrication_activities_by_code("PROD-001", db)
        print(f"✅ Actividades por código: {activities_by_code}")
        
        # 2. Probar get_fabrication_activities_for_orders
        print("\n2️⃣ Probando get_fabrication_activities_for_orders...")
        activities_for_orders = get_fabrication_activities_for_orders(test_orders, db)
        print(f"✅ Actividades para órdenes: {activities_for_orders}")
        
        # 3. Probar get_fabrication_activities_with_details
        print("\n3️⃣ Probando get_fabrication_activities_with_details...")
        activities_with_details = get_fabrication_activities_with_details(test_orders, db)
        print(f"✅ Actividades con detalles: {activities_with_details}")
        
        # 4. Probar calculate_fabrication_minutes_from_performance_and_quantity
        print("\n4️⃣ Probando calculate_fabrication_minutes_from_performance_and_quantity...")
        test_performance = 2.5  # horas
        test_quantity = 100
        minutes = calculate_fabrication_minutes_from_performance_and_quantity(test_performance, test_quantity)
        print(f"✅ Minutos calculados: {test_performance} horas * {test_quantity} = {minutes} minutos")
        
        # 5. Probar get_most_suitable_fabrication_team
        print("\n5️⃣ Probando get_most_suitable_fabrication_team...")
        team_result = get_most_suitable_fabrication_team(db)
        print(f"✅ Equipo más idóneo: {team_result}")
        
        # 6. Probar get_most_suitable_fabrication_team_with_available_programmings
        print("\n6️⃣ Probando get_most_suitable_fabrication_team_with_available_programmings...")
        team_with_programmings = get_most_suitable_fabrication_team_with_available_programmings(db)
        print(f"✅ Equipo con programaciones: {team_with_programmings}")
        
        # 7. Probar get_most_suitable_fabrication_team_with_time_verification
        print("\n7️⃣ Probando get_most_suitable_fabrication_team_with_time_verification...")
        team_with_verification = get_most_suitable_fabrication_team_with_time_verification(db, minutes)
        print(f"✅ Equipo con verificación: {team_with_verification}")
        
        # 8. Probar create_fabrication_task_for_order
        print("\n8️⃣ Probando create_fabrication_task_for_order...")
        fabrication_result = create_fabrication_task_for_order(test_orders, db)
        print(f"✅ Resultado creación tareas: {fabrication_result}")
        
        # 9. Probar create_fabrication_tasks_for_multiple_orders
        print("\n9️⃣ Probando create_fabrication_tasks_for_multiple_orders...")
        multiple_tasks_result = create_fabrication_tasks_for_multiple_orders(test_orders, db)
        print(f"✅ Resultado múltiples tareas: {multiple_tasks_result}")
        
        print("\n🎉 Prueba de compatibilidad completada exitosamente!")
        
    except Exception as e:
        print(f"❌ Error durante la prueba de compatibilidad: {str(e)}")
        import traceback
        traceback.print_exc()
    
    finally:
        db.close()

def test_fabrication_activity_details():
    """Prueba las funciones de detalles de actividades de fabricación"""
    db = SessionLocal()
    
    try:
        print("\n🔍 Probando funciones de detalles de actividades...")
        
        # Probar get_fabrication_activity_details_by_code_and_activity
        print("\n1️⃣ Probando get_fabrication_activity_details_by_code_and_activity...")
        activity_details = get_fabrication_activity_details_by_code_and_activity("PROD-001", "FABRICACION", db)
        print(f"✅ Detalles de actividad: {activity_details}")
        
        # Probar get_fabrication_activity_details_with_minutes_calculation
        print("\n2️⃣ Probando get_fabrication_activity_details_with_minutes_calculation...")
        details_with_minutes = get_fabrication_activity_details_with_minutes_calculation("PROD-001", "FABRICACION", 100, db)
        print(f"✅ Detalles con minutos: {details_with_minutes}")
        
        # Probar get_fabrication_activities_with_minutes_calculation
        print("\n3️⃣ Probando get_fabrication_activities_with_minutes_calculation...")
        test_orders = [{"lote": "TEST001", "quantity": 100, "code": "PROD-001"}]
        activities_with_minutes = get_fabrication_activities_with_minutes_calculation(test_orders, db)
        print(f"✅ Actividades con minutos: {activities_with_minutes}")
        
        print("\n🎉 Prueba de detalles de actividades completada!")
        
    except Exception as e:
        print(f"❌ Error durante la prueba de detalles: {str(e)}")
        import traceback
        traceback.print_exc()
    
    finally:
        db.close()

def test_fabrication_single_task_creation():
    """Prueba la creación de tareas individuales de fabricación"""
    db = SessionLocal()
    
    try:
        print("\n🔧 Probando creación de tareas individuales...")
        
        # Obtener equipo y programaciones
        team_result = get_most_suitable_fabrication_team(db)
        if not team_result.get("success"):
            print("⚠️ No se pudo obtener equipo de fabricación")
            return
        
        team_id = team_result.get("most_suitable_team", {}).get("id")
        available_programmings = get_most_suitable_fabrication_team_with_available_programmings(db)
        
        if not available_programmings.get("success"):
            print("⚠️ No se pudieron obtener programaciones")
            return
        
        programmings = available_programmings.get("available_programmings", {}).get("programmings", [])
        
        if not programmings:
            print("⚠️ No hay programaciones disponibles")
            return
        
        # Datos de prueba
        order_data = {"lote": "TEST001", "quantity": 100, "code": "PROD-001"}
        task_minutes = 120  # 2 horas
        activity_details = {
            "activity": "FABRICACION",
            "description": "Fabricación de producto",
            "performance": 2.0,
            "people": 2
        }
        
        # Probar create_single_fabrication_task
        print("\n1️⃣ Probando create_single_fabrication_task...")
        single_task_result = create_single_fabrication_task(
            order_data, task_minutes, activity_details, programmings, db
        )
        print(f"✅ Resultado tarea individual: {single_task_result}")
        
        # Probar update_fabrication_programming_list_after_task_creation
        print("\n2️⃣ Probando update_fabrication_programming_list_after_task_creation...")
        if single_task_result.get("success"):
            programming_id = single_task_result.get("selected_programming", {}).get("id")
            updated_programmings = update_fabrication_programming_list_after_task_creation(
                programming_id, task_minutes, db
            )
            print(f"✅ Programaciones actualizadas: {len(updated_programmings)} encontradas")
        
        print("\n🎉 Prueba de tareas individuales completada!")
        
    except Exception as e:
        print(f"❌ Error durante la prueba de tareas individuales: {str(e)}")
        import traceback
        traceback.print_exc()
    
    finally:
        db.close()

def test_fabrication_activity_for_order():
    """Prueba la obtención de actividades específicas para órdenes"""
    db = SessionLocal()
    
    try:
        print("\n📋 Probando obtención de actividades específicas...")
        
        # Obtener actividades con minutos
        test_orders = [{"lote": "TEST001", "quantity": 100, "code": "PROD-001"}]
        activities_data = get_fabrication_activities_with_minutes_calculation(test_orders, db)
        
        # Probar get_fabrication_activity_for_order
        print("\n1️⃣ Probando get_fabrication_activity_for_order...")
        order_data = {"lote": "TEST001", "quantity": 100, "code": "PROD-001"}
        specific_activity = get_fabrication_activity_for_order(order_data, activities_data)
        print(f"✅ Actividad específica: {specific_activity}")
        
        print("\n🎉 Prueba de actividades específicas completada!")
        
    except Exception as e:
        print(f"❌ Error durante la prueba de actividades específicas: {str(e)}")
        import traceback
        traceback.print_exc()
    
    finally:
        db.close()

if __name__ == "__main__":
    print("🚀 Iniciando pruebas de compatibilidad del servicio de fabricación...")
    test_fabrication_compatibility_functions()
    test_fabrication_activity_details()
    test_fabrication_single_task_creation()
    test_fabrication_activity_for_order()
    print("\n✨ Todas las pruebas de compatibilidad completadas!")
