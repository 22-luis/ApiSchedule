"""
Script de prueba para verificar las nuevas reglas de asignación de equipos
"""
import sys
import os

# Agregar el directorio raíz al path para importar los módulos
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.services.fabrication_task_service import FabricationTaskService
from app.core.task_config import ManufacturingActivities

def test_new_team_assignment_rules():
    """Prueba las nuevas reglas de asignación de equipos"""
    
    print("🧪 Probando nuevas reglas de asignación de equipos...")
    print("=" * 60)
    
    # Datos simulados de equipos
    mock_teams_data = {
        "teams_by_type": {
            "molino": type('MockTeam', (), {
                'id': 'molino-001',
                'name': 'Equipo Molino'
            })(),
            "fabricado1": type('MockTeam', (), {
                'id': 'fabricado1-001',
                'name': 'Equipo Fabricado 1'
            })(),
            "fabricado2": type('MockTeam', (), {
                'id': 'fabricado2-001',
                'name': 'Equipo Fabricado 2'
            })(),
            "fabricado3": type('MockTeam', (), {
                'id': 'fabricado3-001',
                'name': 'Equipo Fabricado 3'
            })()
        }
    }
    
    # Casos de prueba
    test_cases = [
        # Regla 1: Molino para actividades de molienda
        {
            "name": "Molienda en Pasta",
            "activity": ManufacturingActivities.Mol_pasta.value,
            "description": "Molienda de pasta de tomate",
            "expected_team": "molino",
            "expected_rule": "molienda"
        },
        {
            "name": "Molienda en Polvo",
            "activity": ManufacturingActivities.Mol_polvo.value,
            "description": "Molienda de polvo de chile",
            "expected_team": "molino",
            "expected_rule": "molienda"
        },
        
        # Regla 2: Fabricado 2 para esencia O mezcla líquida
        {
            "name": "Descripción con Esencia",
            "activity": "MEZCLA EN MAQUINA",
            "description": "Mezcla de esencia de vainilla",
            "expected_team": "fabricado2",
            "expected_rule": "esencia_o_mezcla_liquida"
        },
        {
            "name": "Mezcla Líquida",
            "activity": ManufacturingActivities.mez_liquida.value,
            "description": "Mezcla de líquidos",
            "expected_team": "fabricado2",
            "expected_rule": "esencia_o_mezcla_liquida"
        },
        
        # Regla 3: Fabricado 1 para mezcla en máquina o mezcla manual polvo
        {
            "name": "Mezcla en Máquina",
            "activity": ManufacturingActivities.Mez_maquina.value,
            "description": "Mezcla en máquina industrial",
            "expected_team": "fabricado1",
            "expected_rule": "mezcla_fabricado1"
        },
        {
            "name": "Mezcla Manual Polvo",
            "activity": ManufacturingActivities.Mez_polvo.value,
            "description": "Mezcla manual de polvos",
            "expected_team": "fabricado1",
            "expected_rule": "mezcla_fabricado1"
        },
        
        # Regla 4: Fabricado 3 para fabricación de aderezos/jaleas
        {
            "name": "Fabricación de Aderezos",
            "activity": ManufacturingActivities.Fabricacion.value,
            "description": "Fabricación de aderezos para ensalada",
            "expected_team": "fabricado3",
            "expected_rule": "fabricacion_aderezos_jaleas"
        },
        {
            "name": "Fabricación de Jaleas",
            "activity": ManufacturingActivities.Fabricacion.value,
            "description": "Fabricación de jaleas de frutas",
            "expected_team": "fabricado3",
            "expected_rule": "fabricacion_aderezos_jaleas"
        },
        
        # Regla 5: Distribución automática para otras actividades
        {
            "name": "Otra Actividad",
            "activity": "EMPAQUE MANUAL",
            "description": "Empaque manual de productos",
            "expected_team": "fabricado1",  # Primera tarea (impar)
            "expected_rule": "distribucion_fabricado1"
        },
        {
            "name": "Otra Actividad 2",
            "activity": "ENVASADO",
            "description": "Envasado de productos",
            "expected_team": "fabricado3",  # Segunda tarea (par)
            "expected_rule": "distribucion_fabricado3"
        }
    ]
    
    # Ejecutar pruebas
    passed_tests = 0
    total_tests = len(test_cases)
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n📋 Prueba {i}: {test_case['name']}")
        print(f"   Actividad: {test_case['activity']}")
        print(f"   Descripción: {test_case['description']}")
        
        # Llamar al método de asignación
        result = FabricationTaskService.get_specific_team_for_activity(
            test_case['activity'],
            test_case['description'],
            mock_teams_data
        )
        
        if result.get("success"):
            selected_team = result.get("selected_team", {})
            team_type = selected_team.get("type")
            rule_applied = result.get("rule_applied")
            reason = result.get("reason")
            
            print(f"   ✅ Equipo asignado: {team_type}")
            print(f"   📝 Razón: {reason}")
            print(f"   🔧 Regla aplicada: {rule_applied}")
            
            # Verificar resultado esperado
            if (team_type == test_case['expected_team'] and 
                rule_applied == test_case['expected_rule']):
                print(f"   🎯 RESULTADO: PASÓ")
                passed_tests += 1
            else:
                print(f"   ❌ RESULTADO: FALLÓ")
                print(f"      Esperado: {test_case['expected_team']} - {test_case['expected_rule']}")
                print(f"      Obtenido: {team_type} - {rule_applied}")
        else:
            print(f"   ❌ Error: {result.get('reason')}")
    
    # Resumen final
    print("\n" + "=" * 60)
    print(f"📊 RESUMEN DE PRUEBAS:")
    print(f"   ✅ Pruebas pasadas: {passed_tests}/{total_tests}")
    print(f"   ❌ Pruebas fallidas: {total_tests - passed_tests}/{total_tests}")
    print(f"   📈 Porcentaje de éxito: {(passed_tests/total_tests)*100:.1f}%")
    
    if passed_tests == total_tests:
        print("🎉 ¡Todas las pruebas pasaron exitosamente!")
    else:
        print("⚠️  Algunas pruebas fallaron. Revisar la implementación.")
    
    return passed_tests == total_tests

def test_with_real_data():
    """Prueba con datos reales de la base de datos"""
    print("\n" + "=" * 60)
    print("🔍 Probando con datos reales de la base de datos...")
    
    try:
        from app.db.session import SessionLocal
        
        db = SessionLocal()
        
        # Obtener equipos reales
        teams_result = FabricationTaskService.get_most_suitable_fabrication_team(db)
        
        if teams_result.get("success"):
            print("✅ Equipos encontrados en la base de datos:")
            teams_by_type = teams_result.get("teams_by_type", {})
            
            for team_type, team in teams_by_type.items():
                if team:
                    print(f"   - {team_type}: {team.name} (ID: {team.id})")
            
            # Probar con algunas actividades reales
            test_activities = [
                ("MEZCLA EN MAQUINA", "SABOR NARANJA EN POLVO KG"),
                ("MEZCLA EN MAQUINA", "SABOR FRESA EN POLVO KG"),
                ("PESADO", "SABOR NARANJA EN POLVO KG"),  # No debería ser fabricación
            ]
            
            print("\n📋 Probando asignación con actividades reales:")
            for activity, description in test_activities:
                result = FabricationTaskService.get_specific_team_for_activity(
                    activity, description, teams_result
                )
                
                if result.get("success"):
                    selected_team = result.get("selected_team", {})
                    print(f"   ✅ {activity} -> {selected_team.get('name')} ({selected_team.get('type')})")
                    print(f"      Razón: {result.get('reason')}")
                else:
                    print(f"   ❌ {activity} -> Error: {result.get('reason')}")
        
        db.close()
        
    except Exception as e:
        print(f"❌ Error al conectar con la base de datos: {e}")

if __name__ == "__main__":
    # Ejecutar pruebas
    success = test_new_team_assignment_rules()
    
    # Probar con datos reales si las pruebas básicas pasan
    if success:
        test_with_real_data()
    else:
        print("\n⚠️  No se ejecutarán las pruebas con datos reales debido a fallos en las pruebas básicas.")
