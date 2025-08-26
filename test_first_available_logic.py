#!/usr/bin/env python3
"""
Script de prueba para verificar la nueva lógica de "primer espacio disponible"
en la programación de tareas.
"""

import requests
import json
from datetime import datetime, timedelta

# Configuración
BASE_URL = "http://localhost:8000"
API_BASE = f"{BASE_URL}/api/v1"

def test_first_available_logic():
    """Prueba la nueva lógica de primer espacio disponible"""
    
    print("🧪 Probando nueva lógica de 'primer espacio disponible'")
    print("=" * 60)
    
    # 1. Obtener token de autenticación (asumiendo que existe un usuario de prueba)
    print("\n1. Autenticación...")
    auth_response = requests.post(f"{API_BASE}/auth/login", data={
        "username": "admin",  # Ajustar según tu configuración
        "password": "admin"   # Ajustar según tu configuración
    })
    
    if auth_response.status_code != 200:
        print(f"❌ Error de autenticación: {auth_response.status_code}")
        return
    
    token = auth_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    print("✅ Autenticación exitosa")
    
    # 2. Obtener equipos disponibles
    print("\n2. Obteniendo equipos...")
    teams_response = requests.get(f"{API_BASE}/teams/", headers=headers)
    
    if teams_response.status_code != 200:
        print(f"❌ Error al obtener equipos: {teams_response.status_code}")
        return
    
    teams = teams_response.json()
    if not teams:
        print("❌ No hay equipos disponibles")
        return
    
    # Usar el primer equipo disponible
    team = teams[0]
    team_id = team["id"]
    print(f"✅ Equipo seleccionado: {team['name']} (ID: {team_id})")
    
    # 3. Probar el endpoint de primera programación disponible
    print("\n3. Probando endpoint de primera programación disponible...")
    
    # Probar con diferentes duraciones de tareas
    test_durations = [10, 30, 60, 120, 240]  # minutos
    
    for duration in test_durations:
        print(f"\n   Probando tarea de {duration} minutos...")
        
        response = requests.get(
            f"{API_BASE}/programmings/team/{team_id}/first-available-for-task",
            params={"task_minutes": duration},
            headers=headers
        )
        
        if response.status_code == 200:
            result = response.json()
            if result["success"]:
                programming = result["selected_programming"]
                print(f"   ✅ Encontrada programación: {programming['date']}")
                print(f"      - Hora actual: {programming['current_end_time']}")
                print(f"      - Hora final: {programming['final_time']}")
                print(f"      - Tareas existentes: {programming['total_existing_tasks']}")
                print(f"      - Está vacía: {programming['is_empty']}")
            else:
                print(f"   ❌ No se encontró programación disponible: {result['message']}")
        else:
            print(f"   ❌ Error en la petición: {response.status_code}")
            print(f"      Respuesta: {response.text}")
    
    # 4. Probar el endpoint de siguiente horario disponible
    print("\n4. Probando endpoint de siguiente horario disponible...")
    
    # Primero obtener programaciones del equipo
    programmings_response = requests.get(
        f"{API_BASE}/programmings/",
        headers=headers
    )
    
    if programmings_response.status_code == 200:
        programmings = programmings_response.json()
        team_programmings = [p for p in programmings if p.get("team_id") == team_id]
        
        if team_programmings:
            # Usar la primera programación del equipo
            programming_id = team_programmings[0]["id"]
            print(f"   Usando programación: {programming_id}")
            
            response = requests.get(
                f"{API_BASE}/programmings/{programming_id}/next-available-time",
                headers=headers
            )
            
            if response.status_code == 200:
                result = response.json()
                print(f"   ✅ Siguiente horario disponible: {result['next_available_time_formatted']}")
                print(f"      - Total tareas: {result['total_tasks']}")
                print(f"      - Está vacía: {result['is_empty']}")
            else:
                print(f"   ❌ Error: {response.status_code}")
        else:
            print("   ⚠️ No hay programaciones para este equipo")
    else:
        print(f"   ❌ Error al obtener programaciones: {programmings_response.status_code}")
    
    print("\n" + "=" * 60)
    print("✅ Pruebas completadas")

if __name__ == "__main__":
    test_first_available_logic()

