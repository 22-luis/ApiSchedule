#!/usr/bin/env python3
"""
Script para probar la creación de tareas con autenticación real.
Simula exactamente lo que hace el frontend para identificar el problema.
"""

import sys
import os
import requests
import json
from datetime import datetime, timedelta
import time

# Agregar el directorio de la aplicación al path
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

def get_auth_token():
    """Obtiene un token de autenticación válido"""
    
    base_url = "http://localhost:8000/api/v1"
    
    # Datos de login (ajustar según tu configuración)
    login_data = {
        "username": "admin",  # Cambiar por un usuario válido
        "password": "admin123"  # Cambiar por la contraseña correcta
    }
    
    try:
        print("🔐 Intentando autenticarse...")
        response = requests.post(
            f"{base_url}/auth/login",
            data=login_data,  # Usar data en lugar de json para form data
            timeout=10
        )
        
        if response.status_code == 200:
            token_data = response.json()
            token = token_data.get("access_token")
            if token:
                print("✅ Autenticación exitosa")
                return token
            else:
                print("❌ No se encontró token en la respuesta")
                return None
        else:
            print(f"❌ Error de autenticación: {response.status_code}")
            print(f"   Respuesta: {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ Error obteniendo token: {e}")
        return None

def get_valid_test_data(token):
    """Obtiene datos válidos para crear una tarea de prueba"""
    
    base_url = "http://localhost:8000/api/v1"
    headers = {"Authorization": f"Bearer {token}"}
    
    try:
        # 1. Obtener equipos disponibles
        print("📋 Obteniendo equipos disponibles...")
        teams_response = requests.get(f"{base_url}/teams/", headers=headers, timeout=10)
        if teams_response.status_code != 200:
            print(f"❌ Error obteniendo equipos: {teams_response.status_code}")
            return None
            
        teams = teams_response.json()
        if not teams:
            print("❌ No hay equipos disponibles")
            return None
            
        team_id = teams[0]["id"]
        print(f"✅ Equipo seleccionado: {teams[0]['name']} ({team_id})")
        
        # 2. Obtener programaciones disponibles
        print("📋 Obteniendo programaciones disponibles...")
        today = datetime.now().strftime("%Y-%m-%d")
        programmings_response = requests.get(
            f"{base_url}/programmings/", 
            headers=headers, 
            params={"date": today},
            timeout=10
        )
        
        if programmings_response.status_code != 200:
            print(f"❌ Error obteniendo programaciones: {programmings_response.status_code}")
            return None
            
        programmings = programmings_response.json()
        if not programmings:
            print("❌ No hay programaciones disponibles para hoy")
            return None
            
        programming_id = programmings[0]["id"]
        print(f"✅ Programación seleccionada: {programming_id}")
        
        # 3. Obtener códigos disponibles
        print("📋 Obteniendo códigos disponibles...")
        codes_response = requests.get(f"{base_url}/codes/", headers=headers, timeout=10)
        if codes_response.status_code != 200:
            print(f"❌ Error obteniendo códigos: {codes_response.status_code}")
            return None
            
        codes_data = codes_response.json()
        codes = codes_data.get("codes", [])
        if not codes:
            print("❌ No hay códigos disponibles")
            return None
            
        code_id = codes[0]["id"]
        print(f"✅ Código seleccionado: {codes[0]['code']} ({code_id})")
        
        # 4. Crear datos de tarea válidos
        task_data = {
            "minutes": 60,
            "total_time": 60,
            "start_time": datetime.now().isoformat(),
            "end_time": (datetime.now() + timedelta(minutes=60)).isoformat(),
            "teamIds": [team_id],
            "programming_id": programming_id,
            "code_id": code_id,
            "lote": "TEST001",
            "quantity": 10,
            "specification": "Test specification",
            "activity": "TEST ACTIVITY",
            "description": "Test task description",
            "people": 1,
            "performance": 1.0,
            "unit": "kg",
            "type": "produccion"
        }
        
        print("✅ Datos de tarea preparados correctamente")
        return task_data
        
    except Exception as e:
        print(f"❌ Error preparando datos de prueba: {e}")
        return None

def test_task_creation_with_timing(token, task_data):
    """Prueba la creación de tareas midiendo el tiempo de cada paso"""
    
    base_url = "http://localhost:8000/api/v1"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    print("\n🚀 Iniciando prueba de creación de tarea...")
    print("=" * 60)
    
    try:
        # Medir tiempo total
        start_total = time.time()
        
        print("📤 Enviando petición POST...")
        start_request = time.time()
        
        response = requests.post(
            f"{base_url}/tasks/",
            json=task_data,
            headers=headers,
            timeout=30  # Timeout generoso para debug
        )
        
        end_request = time.time()
        request_time = end_request - start_request
        
        print(f"⏱️ Tiempo de petición: {request_time:.2f} segundos")
        print(f"📊 Status Code: {response.status_code}")
        
        if response.status_code == 201:
            print("✅ Tarea creada exitosamente!")
            
            # Intentar parsear la respuesta
            try:
                response_data = response.json()
                task_id = response_data.get("id")
                print(f"🆔 ID de tarea creada: {task_id}")
                
                # Medir tiempo total
                end_total = time.time()
                total_time = end_total - start_total
                print(f"⏱️ Tiempo total: {total_time:.2f} segundos")
                
                return True, task_id
                
            except Exception as e:
                print(f"⚠️ Error parseando respuesta: {e}")
                print(f"📄 Respuesta raw: {response.text[:500]}...")
                return True, None
                
        elif response.status_code == 422:
            print("❌ Error de validación (422)")
            try:
                error_data = response.json()
                print(f"📄 Detalles del error: {json.dumps(error_data, indent=2)}")
            except:
                print(f"📄 Respuesta raw: {response.text}")
            return False, None
            
        else:
            print(f"❌ Error inesperado: {response.status_code}")
            print(f"📄 Respuesta: {response.text}")
            return False, None
            
    except requests.exceptions.Timeout:
        print("❌ TIMEOUT: La petición tardó más de 30 segundos")
        print("   Esto explica el Network Error en el frontend")
        return False, None
        
    except requests.exceptions.ConnectionError as e:
        print(f"❌ ERROR DE CONEXIÓN: {e}")
        return False, None
        
    except Exception as e:
        print(f"❌ ERROR INESPERADO: {e}")
        return False, None

def cleanup_test_task(token, task_id):
    """Limpia la tarea de prueba creada"""
    
    if not task_id:
        return
        
    base_url = "http://localhost:8000/api/v1"
    headers = {"Authorization": f"Bearer {token}"}
    
    try:
        print(f"\n🧹 Limpiando tarea de prueba {task_id}...")
        response = requests.delete(f"{base_url}/tasks/{task_id}", headers=headers, timeout=10)
        
        if response.status_code == 200:
            print("✅ Tarea de prueba eliminada")
        else:
            print(f"⚠️ No se pudo eliminar la tarea: {response.status_code}")
            
    except Exception as e:
        print(f"⚠️ Error limpiando tarea: {e}")

def main():
    """Función principal"""
    print("🔧 DIAGNÓSTICO AVANZADO: Network Error en creación de tareas")
    print("=" * 70)
    
    # 1. Obtener token de autenticación
    token = get_auth_token()
    if not token:
        print("\n❌ No se pudo obtener token de autenticación")
        print("🔧 Verifica que:")
        print("   1. El servidor esté corriendo")
        print("   2. Las credenciales sean correctas")
        print("   3. El endpoint de login funcione")
        return 1
    
    # 2. Obtener datos válidos para la prueba
    task_data = get_valid_test_data(token)
    if not task_data:
        print("\n❌ No se pudieron obtener datos válidos para la prueba")
        return 1
    
    # 3. Probar creación de tarea
    success, task_id = test_task_creation_with_timing(token, task_data)
    
    # 4. Limpiar tarea de prueba
    if success and task_id:
        cleanup_test_task(token, task_id)
    
    # 5. Resumen
    print("\n" + "=" * 70)
    print("📊 RESUMEN:")
    
    if success:
        print("✅ La creación de tareas funciona correctamente")
        print("\n💡 Si el frontend sigue dando Network Error:")
        print("   1. Problema específico del navegador/CORS")
        print("   2. Diferencias en los datos enviados")
        print("   3. Problema de timeout en el cliente")
        print("   4. Error en el manejo de la respuesta")
        print("\n🔧 Recomendaciones:")
        print("   1. Revisar la consola del navegador")
        print("   2. Comparar los datos enviados con los de esta prueba")
        print("   3. Aumentar el timeout en el frontend")
    else:
        print("❌ Hay problemas en la creación de tareas")
        print("\n🔧 Revisar:")
        print("   1. Logs del servidor")
        print("   2. Base de datos")
        print("   3. Servicios dependientes")
    
    return 0 if success else 1

if __name__ == "__main__":
    exit(main())