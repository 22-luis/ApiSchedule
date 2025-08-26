"""
Script de prueba para verificar el funcionamiento del servicio de fabricación.
"""
import sys
import os
from datetime import datetime, date

# Agregar el directorio raíz al path para importar los módulos
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy.orm import Session
from app.db.database import SessionLocal
from app.services.fabrication_task_service import FabricationTaskService
from app.models.order import Order
from app.models.state import OrderStatus

def test_fabrication_service():
    """Prueba básica del servicio de fabricación"""
    db = SessionLocal()
    
    try:
        print("🧪 Iniciando prueba del servicio de fabricación...")
        
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
        
        # Probar extracción de datos
        print("\n1️⃣ Probando extracción de datos...")
        extracted_data = FabricationTaskService.extract_order_data(test_orders)
        print(f"✅ Datos extraídos: {extracted_data}")
        
        # Probar obtención de actividades
        print("\n2️⃣ Probando obtención de actividades...")
        activities_data = FabricationTaskService.get_activities_for_orders(extracted_data, db)
        print(f"✅ Actividades obtenidas: {activities_data}")
        
        # Probar filtrado de actividades de fabricación
        print("\n3️⃣ Probando filtrado de actividades de fabricación...")
        fabrication_activities = FabricationTaskService.filter_fabrication_activities(activities_data)
        print(f"✅ Actividades de fabricación: {fabrication_activities}")
        
        # Probar cálculo de minutos
        print("\n4️⃣ Probando cálculo de minutos...")
        test_performance = 2.5  # horas
        test_quantity = 100
        minutes = FabricationTaskService.calculate_minutes_from_performance_and_quantity(
            test_performance, test_quantity
        )
        print(f"✅ Minutos calculados: {test_performance} horas * {test_quantity} = {minutes} minutos")
        
        # Probar obtención de equipo de fabricación
        print("\n5️⃣ Probando obtención de equipo de fabricación...")
        team_result = FabricationTaskService.get_most_suitable_fabrication_team(db)
        print(f"✅ Resultado equipo: {team_result}")
        
        # Probar obtención de programaciones disponibles
        if team_result.get("success"):
            team_id = team_result.get("most_suitable_team", {}).get("id")
            print(f"\n6️⃣ Probando obtención de programaciones para equipo {team_id}...")
            programmings = FabricationTaskService.get_available_programmings_for_team(team_id, db)
            print(f"✅ Programaciones disponibles: {len(programmings)} encontradas")
        
        # Probar función principal completa
        print("\n7️⃣ Probando función principal completa...")
        result = FabricationTaskService.create_fabrication_tasks_for_orders(extracted_data, db)
        print(f"✅ Resultado completo: {result}")
        
        print("\n🎉 Prueba completada exitosamente!")
        
    except Exception as e:
        print(f"❌ Error durante la prueba: {str(e)}")
        import traceback
        traceback.print_exc()
    
    finally:
        db.close()

def test_with_real_orders():
    """Prueba con órdenes reales de la base de datos"""
    db = SessionLocal()
    
    try:
        print("\n🔍 Probando con órdenes reales de la base de datos...")
        
        # Obtener algunas órdenes recientes
        recent_orders = db.query(Order).order_by(Order.lote.desc()).limit(3).all()
        
        if not recent_orders:
            print("⚠️ No se encontraron órdenes en la base de datos")
            return
        
        print(f"📋 Órdenes encontradas: {len(recent_orders)}")
        for order in recent_orders:
            print(f"  - Lote: {order.lote}, Código: {order.code}, Cantidad: {order.quantity}")
        
        # Extraer datos de las órdenes
        extracted_orders = FabricationTaskService.extract_order_data(recent_orders)
        
        # Probar el servicio completo
        result = FabricationTaskService.create_fabrication_tasks_for_orders(extracted_orders, db)
        
        print(f"✅ Resultado con órdenes reales: {result}")
        
    except Exception as e:
        print(f"❌ Error durante la prueba con órdenes reales: {str(e)}")
        import traceback
        traceback.print_exc()
    
    finally:
        db.close()

if __name__ == "__main__":
    print("🚀 Iniciando pruebas del servicio de fabricación...")
    test_fabrication_service()
    test_with_real_orders()
    print("\n✨ Todas las pruebas completadas!")
