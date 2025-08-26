"""
Script de prueba para verificar la lógica de asignación de equipos del servicio de fabricación
"""
import sys
import os
from datetime import datetime, date

# Agregar el directorio raíz al path para importar los módulos
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.services.fabrication_task_service import FabricationTaskService
from app.db.session import SessionLocal

def test_team_assignment_logic():
    """Prueba la lógica de asignación de equipos según las reglas específicas"""
    
    print("🧪 Probando lógica de asignación de equipos...")
    
    # Simular datos de equipos (como los devolvería get_most_suitable_fabrication_team)
    teams_data = {
        "teams_by_type": {
            "molino": type('Team', (), {
                'id': 'molino-001',
                'name': 'Molino Principal'
            })(),
            "fabricado1": type('Team', (), {
                'id': 'fabricado1-001',
                'name': 'Fabricado 1'
            })(),
            "fabricado2": type('Team', (), {
                'id': 'fabricado2-001',
                'name': 'Fabricado 2'
            })(),
            "fabricado3": type('Team', (), {
                'id': 'fabricado3-001',
                'name': 'Fabricado 3'
            })()
        }
    }
    
    # Casos de prueba
    test_cases = [
        {
            "name": "Actividad de molienda en pasta",
            "activity": "MOLIENDA EN PASTA",
            "description": "Molienda de ingredientes en pasta",
            "expected_team": "molino",
            "expected_rule": "molienda"
        },
        {
            "name": "Actividad de molienda en polvo",
            "activity": "MOLIENDA EN POLVO",
            "description": "Molienda de ingredientes en polvo",
            "expected_team": "molino",
            "expected_rule": "molienda"
        },
        {
            "name": "Descripción con esencia",
            "activity": "MEZCLA EN MAQUINA",
            "description": "Mezcla de esencia de vainilla",
            "expected_team": "fabricado2",
            "expected_rule": "esencia"
        },
        {
            "name": "Descripción con ESENCIA (mayúsculas)",
            "activity": "FABRICACION DE ADEREZOS",
            "description": "Fabricación con ESENCIA de limón",
            "expected_team": "fabricado2",
            "expected_rule": "esencia"
        },
        {
            "name": "Actividad de mezcla normal",
            "activity": "MEZCLA EN MAQUINA",
            "description": "Mezcla de ingredientes básicos",
            "expected_team": "fabricado1",  # Primera tarea (impar)
            "expected_rule": "distribucion_fabricado1"
        },
        {
            "name": "Actividad de fabricación normal",
            "activity": "FABRICACION DE ADEREZOS, JALEAS",
            "description": "Fabricación de aderezos",
            "expected_team": "fabricado3",  # Segunda tarea (par)
            "expected_rule": "distribucion_fabricado3"
        },
        {
            "name": "Tercera tarea normal",
            "activity": "MEZCLA MANUAL POLVO",
            "description": "Mezcla manual de polvos",
            "expected_team": "fabricado1",  # Tercera tarea (impar)
            "expected_rule": "distribucion_fabricado1"
        }
    ]
    
    print(f"\n📋 Ejecutando {len(test_cases)} casos de prueba...")
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n{i}️⃣ {test_case['name']}")
        print(f"   Actividad: {test_case['activity']}")
        print(f"   Descripción: {test_case['description']}")
        
        # Probar la asignación
        result = FabricationTaskService.get_specific_team_for_activity(
            test_case['activity'],
            test_case['description'],
            teams_data
        )
        
        if result.get("success"):
            selected_team = result.get("selected_team")
            team_type = selected_team.get("type")
            rule_applied = result.get("rule_applied")
            
            print(f"   ✅ Equipo asignado: {selected_team.get('name')} ({team_type})")
            print(f"   📝 Regla aplicada: {rule_applied}")
            print(f"   💡 Razón: {result.get('reason')}")
            
            # Verificar que coincida con lo esperado
            if team_type == test_case['expected_team'] and rule_applied == test_case['expected_rule']:
                print(f"   🎯 RESULTADO: CORRECTO")
            else:
                print(f"   ❌ RESULTADO: INCORRECTO")
                print(f"      Esperado: {test_case['expected_team']} - {test_case['expected_rule']}")
                print(f"      Obtenido: {team_type} - {rule_applied}")
        else:
            print(f"   ❌ Error: {result.get('reason')}")
    
    print("\n🎉 Prueba de lógica de asignación completada!")

def test_team_distribution():
    """Prueba la distribución alternada entre Fabricado 1 y 3"""
    
    print("\n🔄 Probando distribución alternada entre Fabricado 1 y 3...")
    
    # Simular datos de equipos
    teams_data = {
        "teams_by_type": {
            "fabricado1": type('Team', (), {
                'id': 'fabricado1-001',
                'name': 'Fabricado 1'
            })(),
            "fabricado3": type('Team', (), {
                'id': 'fabricado3-001',
                'name': 'Fabricado 3'
            })()
        }
    }
    
    # Resetear el contador de distribución
    if hasattr(FabricationTaskService, '_distribution_counter'):
        delattr(FabricationTaskService, '_distribution_counter')
    
    # Probar 6 tareas para ver la alternancia
    for i in range(1, 7):
        result = FabricationTaskService.get_specific_team_for_activity(
            "MEZCLA EN MAQUINA",
            f"Tarea de prueba #{i}",
            teams_data
        )
        
        if result.get("success"):
            team_type = result.get("selected_team", {}).get("type")
            rule_applied = result.get("rule_applied")
            print(f"   Tarea #{i}: {team_type} - {rule_applied}")
        else:
            print(f"   Tarea #{i}: Error - {result.get('reason')}")
    
    print("✅ Prueba de distribución completada!")

def test_database_integration():
    """Prueba la integración con la base de datos"""
    
    print("\n🗄️ Probando integración con base de datos...")
    
    db = SessionLocal()
    
    try:
        # Obtener equipos reales de la base de datos
        teams_result = FabricationTaskService.get_most_suitable_fabrication_team(db)
        
        if teams_result.get("success"):
            print("✅ Equipos obtenidos de la base de datos:")
            teams_by_type = teams_result.get("teams_by_type", {})
            
            for team_type, team in teams_by_type.items():
                if team:
                    print(f"   {team_type}: {team.name} (ID: {team.id})")
                else:
                    print(f"   {team_type}: No encontrado")
            
            # Probar asignación con equipos reales
            print("\n🔍 Probando asignación con equipos reales...")
            
            test_activities = [
                ("MOLIENDA EN PASTA", "Molienda de ingredientes"),
                ("MEZCLA EN MAQUINA", "Mezcla con esencia de vainilla"),
                ("FABRICACION DE ADEREZOS", "Fabricación normal"),
                ("MEZCLA MANUAL POLVO", "Mezcla manual")
            ]
            
            for activity, description in test_activities:
                result = FabricationTaskService.get_specific_team_for_activity(
                    activity, description, teams_result
                )
                
                if result.get("success"):
                    team_info = result.get("selected_team", {})
                    print(f"   {activity}: {team_info.get('name')} ({team_info.get('type')})")
                else:
                    print(f"   {activity}: Error - {result.get('reason')}")
        
        else:
            print(f"❌ Error al obtener equipos: {teams_result.get('message')}")
    
    except Exception as e:
        print(f"❌ Error durante la prueba de base de datos: {str(e)}")
    
    finally:
        db.close()

if __name__ == "__main__":
    print("🚀 Iniciando pruebas de asignación de equipos...")
    
    test_team_assignment_logic()
    test_team_distribution()
    test_database_integration()
    
    print("\n✨ Todas las pruebas de asignación de equipos completadas!")
