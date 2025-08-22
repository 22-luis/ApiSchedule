#!/usr/bin/env python3
"""
Script de prueba para los endpoints de programaciones disponibles.
Este script prueba los nuevos endpoints creados para obtener programaciones disponibles por equipo.
"""

import requests
import json
from datetime import date, timedelta
from typing import Dict, Any

# Configuración
BASE_URL = "http://localhost:8000"
API_BASE = f"{BASE_URL}/api/v1"

def login(username: str, password: str) -> str:
    """Inicia sesión y obtiene el token JWT"""
    response = requests.post(f"{API_BASE}/auth/login", data={
        "username": username,
        "password": password
    })
    
    if response.status_code == 200:
        data = response.json()
        return data["access_token"]
    else:
        raise Exception(f"Error de login: {response.status_code} - {response.text}")

def get_headers(token: str) -> Dict[str, str]:
    """Obtiene los headers con el token de autorización"""
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

def test_get_available_programmings(token: str, team_uuid: str):
    """Prueba el endpoint de obtener programaciones disponibles (con creación automática)"""
    print("\n🔍 Probando GET /programmings/team/{team_uuid}/available")
    
    headers = get_headers(token)
    url = f"{API_BASE}/programmings/team/{team_uuid}/available"
    
    try:
        response = requests.get(url, headers=headers)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Respuesta exitosa:")
            print(f"   Team ID: {data['team_id']}")
            print(f"   Team Name: {data['team_name']}")
            print(f"   Programaciones disponibles: {len(data['available_programmings'])}")
            
            for prog in data['available_programmings']:
                print(f"     - ID: {prog['id']}")
                print(f"       Fecha: {prog['date']}")
                print(f"       Equipo: {prog['team_name']}")
            
            return data
        else:
            print(f"❌ Error: {response.status_code}")
            print(f"   Respuesta: {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ Excepción: {e}")
        return None

def test_get_only_available_programmings(token: str, team_uuid: str):
    """Prueba el endpoint de obtener solo programaciones disponibles existentes"""
    print("\n🔍 Probando GET /programmings/team/{team_uuid}/available-only")
    
    headers = get_headers(token)
    url = f"{API_BASE}/programmings/team/{team_uuid}/available-only"
    
    try:
        response = requests.get(url, headers=headers)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Respuesta exitosa:")
            print(f"   Team ID: {data['team_id']}")
            print(f"   Team Name: {data['team_name']}")
            print(f"   Programaciones disponibles: {len(data['available_programmings'])}")
            
            for prog in data['available_programmings']:
                print(f"     - ID: {prog['id']}")
                print(f"       Fecha: {prog['date']}")
                print(f"       Equipo: {prog['team_name']}")
            
            return data
        else:
            print(f"❌ Error: {response.status_code}")
            print(f"   Respuesta: {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ Excepción: {e}")
        return None

def test_create_next_available_programming(token: str, team_uuid: str):
    """Prueba el endpoint de crear nueva programación disponible"""
    print("\n🔍 Probando POST /programmings/team/{team_uuid}/create-next-available")
    
    headers = get_headers(token)
    url = f"{API_BASE}/programmings/team/{team_uuid}/create-next-available"
    
    try:
        response = requests.post(url, headers=headers)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Programación creada exitosamente:")
            print(f"   ID: {data['id']}")
            print(f"   Equipo: {data['team_name']}")
            print(f"   Fecha: {data['date']}")
            return data
        else:
            print(f"❌ Error: {response.status_code}")
            print(f"   Respuesta: {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ Excepción: {e}")
        return None

def test_team_not_found(token: str):
    """Prueba el comportamiento cuando el equipo no existe"""
    print("\n🔍 Probando con equipo inexistente")
    
    fake_team_uuid = "00000000-0000-0000-0000-000000000000"
    headers = get_headers(token)
    url = f"{API_BASE}/programmings/team/{fake_team_uuid}/available"
    
    try:
        response = requests.get(url, headers=headers)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 404:
            print("✅ Correcto: Equipo no encontrado")
        else:
            print(f"❌ Comportamiento inesperado: {response.status_code}")
            print(f"   Respuesta: {response.text}")
            
    except Exception as e:
        print(f"❌ Excepción: {e}")

def main():
    """Función principal de pruebas"""
    print("🚀 Iniciando pruebas de endpoints de programaciones disponibles")
    print("=" * 60)
    
    # Credenciales de prueba (ajustar según tu configuración)
    username = "admin"  # Cambiar por un usuario válido
    password = "admin123"  # Cambiar por la contraseña correcta
    
    try:
        # Login
        print(f"🔐 Iniciando sesión como {username}...")
        token = login(username, password)
        print("✅ Login exitoso")
        
        # Obtener lista de equipos para pruebas
        print("\n📋 Obteniendo lista de equipos...")
        headers = get_headers(token)
        teams_response = requests.get(f"{API_BASE}/teams/", headers=headers)
        
        if teams_response.status_code == 200:
            teams = teams_response.json()
            if teams:
                team_uuid = str(teams[0]['id'])  # Usar el primer equipo
                team_name = teams[0]['name']
                print(f"✅ Usando equipo: {team_name} ({team_uuid})")
                
                # Ejecutar pruebas
                test_get_available_programmings(token, team_uuid)
                test_get_only_available_programmings(token, team_uuid)
                test_create_next_available_programming(token, team_uuid)
                test_team_not_found(token)
                
            else:
                print("❌ No hay equipos disponibles para las pruebas")
        else:
            print(f"❌ Error obteniendo equipos: {teams_response.status_code}")
            
    except Exception as e:
        print(f"❌ Error en las pruebas: {e}")
    
    print("\n" + "=" * 60)
    print("🏁 Pruebas completadas")

if __name__ == "__main__":
    main()
