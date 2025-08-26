"""
Script de prueba para verificar que el servicio de fabricación funciona correctamente
con los datos que causaron el error de multiplicación None * int
"""
import sys
import os
from datetime import datetime, date

# Agregar el directorio raíz al path para importar los módulos
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.services.fabrication_task_service import FabricationTaskService
from app.db.session import SessionLocal

def test_fabrication_with_real_data():
    """Prueba el servicio de fabricación con los datos reales que causaron el error"""
    
    print("🧪 Probando servicio de fabricación con datos reales...")
    
    # Datos de las órdenes que causaron el error
    test_orders = [
        {
            "lote": 88537,
            "quantity": 1,
            "code": "K1421"
        },
        {
            "lote": 88538,
            "quantity": 20,
            "code": "P1121"
        },
        {
            "lote": 88539,
            "quantity": 5,
            "code": "P1031"
        }
    ]
    
    print(f"📋 Probando con {len(test_orders)} órdenes:")
    for order in test_orders:
        print(f"   - Lote: {order['lote']}, Cantidad: {order['quantity']}, Código: {order['code']}")
    
    db = SessionLocal()
    
    try:
        print("\n🔍 Paso 1: Obteniendo actividades de fabricación...")
        
        # Obtener actividades de fabricación con minutos calculados
        fabrication_activities_data = FabricationTaskService.get_fabrication_activities_with_minutes(
            test_orders, db
        )
        
        if fabrication_activities_data:
            print("✅ Actividades de fabricación obtenidas exitosamente")
            
            # Mostrar información de las actividades encontradas
            fabrication_activities_with_minutes = fabrication_activities_data.get(
                "fabrication_activities_with_minutes", {}
            ).get("fabrication_activities_with_minutes_by_code", {})
            
            print(f"\n📊 Actividades de fabricación encontradas: {len(fabrication_activities_with_minutes)} códigos")
            
            for code, code_data in fabrication_activities_with_minutes.items():
                print(f"\n   Código: {code}")
                activities = code_data.get("fabrication_activities_with_minutes", [])
                print(f"   Actividades: {len(activities)}")
                
                for i, activity in enumerate(activities, 1):
                    activity_data = activity.get("activity_data", {})
                    minutes_calc = activity.get("minutes_calculation", {})
                    
                    print(f"     {i}. {activity_data.get('activity', 'N/A')}")
                    print(f"        Descripción: {activity_data.get('description', 'N/A')}")
                    print(f"        Performance: {activity_data.get('performance', 'None')}")
                    print(f"        Time: {activity_data.get('time', 'None')}")
                    print(f"        People: {activity_data.get('people', 'None')}")
                    print(f"        Unit: {activity_data.get('unit', 'None')}")
                    print(f"        Type: {activity_data.get('type', 'None')}")
                    print(f"        Minutos calculados: {minutes_calc.get('calculated_minutes', 'N/A')}")
                    print(f"        Fórmula: {minutes_calc.get('formula', 'N/A')}")
        else:
            print("❌ No se pudieron obtener actividades de fabricación")
            return
        
        print("\n🔍 Paso 2: Obteniendo equipos de fabricación...")
        
        # Obtener equipos de fabricación
        teams_result = FabricationTaskService.get_most_suitable_fabrication_team(db)
        
        if teams_result.get("success"):
            print("✅ Equipos de fabricación obtenidos exitosamente")
            
            teams_by_type = teams_result.get("teams_by_type", {})
            print(f"\n📊 Equipos disponibles:")
            
            for team_type, team in teams_by_type.items():
                if team:
                    print(f"   {team_type}: {team.name} (ID: {team.id})")
                else:
                    print(f"   {team_type}: No encontrado")
        else:
            print(f"❌ Error al obtener equipos: {teams_result.get('message')}")
            return
        
        print("\n🔍 Paso 3: Probando asignación de equipos...")
        
        # Probar asignación de equipos para cada actividad
        for code, code_data in fabrication_activities_with_minutes.items():
            activities = code_data.get("fabrication_activities_with_minutes", [])
            
            for activity in activities:
                activity_data = activity.get("activity_data", {})
                activity_name = activity_data.get("activity", "")
                activity_description = activity_data.get("description", "")
                
                print(f"\n   Probando: {activity_name}")
                print(f"   Descripción: {activity_description}")
                
                team_selection = FabricationTaskService.get_specific_team_for_activity(
                    activity_name, activity_description, teams_result
                )
                
                if team_selection.get("success"):
                    selected_team = team_selection.get("selected_team", {})
                    print(f"   ✅ Equipo asignado: {selected_team.get('name')} ({selected_team.get('type')})")
                    print(f"   📝 Razón: {team_selection.get('reason')}")
                    print(f"   🎯 Regla aplicada: {team_selection.get('rule_applied')}")
                else:
                    print(f"   ❌ Error: {team_selection.get('reason')}")
        
        print("\n🔍 Paso 4: Ejecutando servicio completo...")
        
        # Ejecutar el servicio completo
        result = FabricationTaskService.create_fabrication_tasks_for_orders(test_orders, db)
        
        if result.get("success"):
            print("✅ Servicio de fabricación ejecutado exitosamente")
            
            tasks_created = result.get("tasks_created", 0)
            total_orders = result.get("total_orders", 0)
            
            print(f"\n📊 Resultados:")
            print(f"   Tareas creadas: {tasks_created}")
            print(f"   Total de órdenes: {total_orders}")
            
            # Mostrar resumen de asignaciones de equipos
            team_assignments = result.get("team_assignments_summary", {})
            if team_assignments:
                print(f"\n🏭 Asignaciones por equipo:")
                for team_type, count in team_assignments.items():
                    print(f"   {team_type}: {count} tareas")
            
            # Mostrar tareas creadas
            created_tasks = result.get("created_tasks", [])
            if created_tasks:
                print(f"\n📋 Tareas creadas:")
                for i, task in enumerate(created_tasks, 1):
                    order_data = task.get("order_data", {})
                    team_assignment = task.get("team_assignment", {})
                    order_task = task.get("order_task", {})
                    
                    print(f"   {i}. Lote: {order_data.get('lote')}, Código: {order_data.get('code')}")
                    print(f"      Equipo: {team_assignment.get('team_name')} ({team_assignment.get('team_type')})")
                    print(f"      Razón: {team_assignment.get('assignment_reason')}")
                    print(f"      Minutos: {order_task.get('minutes', 'N/A')}")
                    print(f"      Descripción: {order_task.get('description', 'N/A')}")
            
            # Mostrar órdenes fallidas
            failed_orders = result.get("failed_orders", [])
            if failed_orders:
                print(f"\n❌ Órdenes fallidas:")
                for i, failed_order in enumerate(failed_orders, 1):
                    order_data = failed_order.get("order_data", {})
                    reason = failed_order.get("reason", "Error desconocido")
                    print(f"   {i}. Lote: {order_data.get('lote')}, Código: {order_data.get('code')}")
                    print(f"      Razón: {reason}")
        else:
            print(f"❌ Error en el servicio: {result.get('message')}")
    
    except Exception as e:
        print(f"❌ Error durante la prueba: {str(e)}")
        import traceback
        traceback.print_exc()
    
    finally:
        db.close()

def test_performance_none_handling():
    """Prueba específicamente el manejo de performance None"""
    
    print("\n🧪 Probando manejo de performance None...")
    
    # Simular datos con performance None
    test_orders = [
        {
            "lote": 88538,
            "quantity": 20,
            "code": "P1121"
        }
    ]
    
    db = SessionLocal()
    
    try:
        # Obtener actividades de fabricación
        fabrication_activities_data = FabricationTaskService.get_fabrication_activities_with_minutes(
            test_orders, db
        )
        
        if fabrication_activities_data:
            fabrication_activities_with_minutes = fabrication_activities_data.get(
                "fabrication_activities_with_minutes", {}
            ).get("fabrication_activities_with_minutes_by_code", {})
            
            for code, code_data in fabrication_activities_with_minutes.items():
                activities = code_data.get("fabrication_activities_with_minutes", [])
                
                for activity in activities:
                    activity_data = activity.get("activity_data", {})
                    minutes_calc = activity.get("minutes_calculation", {})
                    
                    performance = activity_data.get("performance")
                    calculated_minutes = minutes_calc.get("calculated_minutes")
                    formula = minutes_calc.get("formula")
                    
                    print(f"   Actividad: {activity_data.get('activity')}")
                    print(f"   Performance: {performance}")
                    print(f"   Minutos calculados: {calculated_minutes}")
                    print(f"   Fórmula: {formula}")
                    
                    if performance is None:
                        print("   ✅ Performance None manejado correctamente")
                    else:
                        print("   ⚠️ Performance no es None")
        
        print("✅ Prueba de manejo de performance None completada")
    
    except Exception as e:
        print(f"❌ Error en prueba de performance None: {str(e)}")
    
    finally:
        db.close()

if __name__ == "__main__":
    print("🚀 Iniciando pruebas del servicio de fabricación...")
    
    test_fabrication_with_real_data()
    test_performance_none_handling()
    
    print("\n✨ Todas las pruebas del servicio de fabricación completadas!")
