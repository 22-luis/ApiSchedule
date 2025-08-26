#!/usr/bin/env python3
"""
Script de prueba específico para verificar que el sistema priorice las fechas más antiguas
cronológicamente, independientemente del tiempo ocupado.
"""

import requests
import json
from datetime import datetime, timedelta

# Configuración
BASE_URL = "http://localhost:8000"
API_BASE = f"{BASE_URL}/api/v1"

def test_chronological_priority():
    """Prueba que el sistema priorice fechas más antiguas cronológicamente"""
    
    print("🧪 Probando prioridad cronológica: fechas más antiguas primero")
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
    
    # Ordenar por fecha para mostrar cronológicamente
    team_programmings.sort(key=lambda x: x.get("date", ""))
    
    print(f"✅ Programaciones encontradas: {len(team_programmings)}")
    print("\n📅 Programaciones ordenadas cronológicamente:")
    for i, prog in enumerate(team_programmings):
        tasks_count = len(prog.get("tasks", []))
        print(f"   {i+1}. {prog['date']}: {tasks_count} tareas")
    
    # 4. Probar con diferentes duraciones de tareas
    print("\n4. Probando primera programación disponible...")
    
    test_durations = [30, 60, 120, 240]  # minutos
    
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
                selected_date = programming['date']
                
                # Encontrar la posición cronológica de la programación seleccionada
                chronological_position = None
                for i, prog in enumerate(team_programmings):
                    if prog['date'] == selected_date:
                        chronological_position = i + 1
                        break
                
                print(f"   ✅ SELECCIONADA: {selected_date} (posición cronológica: {chronological_position})")
                print(f"      - Hora actual: {programming['current_end_time']}")
                print(f"      - Hora final: {programming['final_time']}")
                print(f"      - Tareas existentes: {programming['total_existing_tasks']}")
                print(f"      - Está vacía: {programming['is_empty']}")
                
                # Verificar si seleccionó la fecha más antigua disponible
                if chronological_position == 1:
                    print(f"   🎯 PERFECTO: Seleccionó la fecha más antigua disponible")
                else:
                    print(f"   ⚠️ ATENCIÓN: Seleccionó la posición {chronological_position}, no la más antigua")
                    
                    # Mostrar las fechas más antiguas que no fueron seleccionadas
                    print(f"   📋 Fechas más antiguas no seleccionadas:")
                    for i in range(chronological_position - 1):
                        older_prog = team_programmings[i]
                        print(f"      - {older_prog['date']}: {len(older_prog.get('tasks', []))} tareas")
            else:
                print(f"   ❌ No se encontró programación disponible: {result['message']}")
        else:
            print(f"   ❌ Error en la petición: {response.status_code}")
            print(f"      Respuesta: {response.text}")
    
    # 5. Verificar el siguiente horario disponible en cada programación
    print("\n5. Verificando siguiente horario disponible en cada programación...")
    
    for i, prog in enumerate(team_programmings[:5]):  # Solo las primeras 5
        programming_id = prog["id"]
        print(f"\n   📅 Programación {i+1}: {prog['date']} (ID: {programming_id}):")
        
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
    print("✅ Pruebas de prioridad cronológica completadas")

if __name__ == "__main__":
    test_chronological_priority()

