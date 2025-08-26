#!/usr/bin/env python3
"""
Script de prueba específico para simular el escenario donde el sistema
debería usar el espacio disponible en un día con tareas existentes.
"""

import requests
import json
from datetime import datetime, timedelta

# Configuración
BASE_URL = "http://localhost:8000"
API_BASE = f"{BASE_URL}/api/v1"

def test_specific_scenario():
    """Prueba el escenario específico donde hay días con tareas pero espacio disponible"""
    
    print("🧪 Probando escenario específico: días con tareas pero espacio disponible")
    print("=" * 70)
    
    # 1. Autenticación
    print("\n1. Autenticación...")
    auth_response = requests.post(f"{API_BASE}/auth/login", data={
        "username": "admin",
        "password": "admin"
    })
    
    if auth_response.status_code != 200:
        print(f"❌ Error de autenticación: {auth_response.status_code}")
        return
    
    token = auth_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    print("✅ Autenticación exitosa")
    
    # 2. Obtener equipo Pesado
    print("\n2. Obteniendo equipo Pesado...")
    teams_response = requests.get(f"{API_BASE}/teams/", headers=headers)
    
    if teams_response.status_code != 200:
        print(f"❌ Error al obtener equipos: {teams_response.status_code}")
        return
    
    teams = teams_response.json()
    pesado_team = None
    for team in teams:
        if "pesado" in team["name"].lower():
            pesado_team = team
            break
    
    if not pesado_team:
        print("❌ No se encontró equipo Pesado")
        return
    
    team_id = pesado_team["id"]
    print(f"✅ Equipo encontrado: {pesado_team['name']} (ID: {team_id})")
    
    # 3. Obtener programaciones del equipo
    print("\n3. Obteniendo programaciones del equipo...")
    programmings_response = requests.get(f"{API_BASE}/programmings/", headers=headers)
    
    if programmings_response.status_code != 200:
        print(f"❌ Error al obtener programaciones: {programmings_response.status_code}")
        return
    
    programmings = programmings_response.json()
    team_programmings = [p for p in programmings if p.get("team_id") == team_id]
    
    print(f"✅ Programaciones encontradas: {len(team_programmings)}")
    for prog in team_programmings:
        print(f"   - {prog['date']}: {prog.get('tasks', [])} tareas")
    
    # 4. Probar con diferentes duraciones de tareas
    print("\n4. Probando primera programación disponible...")
    
    test_durations = [10, 30, 60, 120, 240]  # minutos
    
    for duration in test_durations:
        print(f"\n   🔍 Probando tarea de {duration} minutos...")
        
        response = requests.get(
            f"{API_BASE}/programmings/team/{team_id}/first-available-for-task",
            params={"task_minutes": duration},
            headers=headers
        )
        
        if response.status_code == 200:
            result = response.json()
            if result["success"]:
                programming = result["selected_programming"]
                print(f"   ✅ SELECCIONADA: {programming['date']}")
                print(f"      - Hora actual: {programming['current_end_time']}")
                print(f"      - Hora final: {programming['final_time']}")
                print(f"      - Tareas existentes: {programming['total_existing_tasks']}")
                print(f"      - Está vacía: {programming['is_empty']}")
                
                # Verificar si seleccionó un día con tareas existentes
                if programming['total_existing_tasks'] > 0:
                    print(f"   🎯 PERFECTO: Seleccionó día con tareas existentes")
                else:
                    print(f"   ⚠️ ATENCIÓN: Seleccionó día vacío")
            else:
                print(f"   ❌ No se encontró programación disponible: {result['message']}")
        else:
            print(f"   ❌ Error en la petición: {response.status_code}")
            print(f"      Respuesta: {response.text}")
    
    # 5. Probar el endpoint de siguiente horario disponible para cada programación
    print("\n5. Verificando siguiente horario disponible en cada programación...")
    
    for prog in team_programmings[:3]:  # Solo las primeras 3
        programming_id = prog["id"]
        print(f"\n   📅 Programación {prog['date']} (ID: {programming_id}):")
        
        response = requests.get(
            f"{API_BASE}/programmings/{programming_id}/next-available-time",
            headers=headers
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"   ✅ Siguiente horario: {result['next_available_time_formatted']}")
            print(f"      - Total tareas: {result['total_tasks']}")
            print(f"      - Está vacía: {result['is_empty']}")
            
            # Calcular cuánto espacio hay disponible
            if not result['is_empty']:
                next_time = datetime.fromisoformat(result['next_available_time'])
                end_of_day = datetime.combine(next_time.date(), datetime.min.time().replace(hour=17, minute=40))
                available_minutes = (end_of_day - next_time).total_seconds() / 60
                print(f"      - Espacio disponible: {available_minutes:.0f} minutos")
        else:
            print(f"   ❌ Error: {response.status_code}")
    
    print("\n" + "=" * 70)
    print("✅ Pruebas completadas")

if __name__ == "__main__":
    test_specific_scenario()

