#!/usr/bin/env python3
"""
Script de diagnóstico para el problema de Network Error al crear tareas.
Simula la creación de una tarea para identificar dónde está fallando.
"""

import sys
import os
import requests
import json
from datetime import datetime, timedelta
import uuid

# Agregar el directorio de la aplicación al path
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

def test_task_creation_endpoint():
    """Prueba el endpoint de creación de tareas directamente"""
    
    # URL del endpoint
    base_url = "http://localhost:8000/api/v1"
    
    print("🔍 Probando conectividad con el backend...")
    
    # 1. Probar conectividad básica
    try:
        response = requests.get(f"{base_url}/", timeout=5)
        print(f"✅ Backend responde: {response.status_code}")
    except requests.exceptions.RequestException as e:
        print(f"❌ Error de conectividad: {e}")
        return False
    
    # 2. Probar endpoint de tareas sin autenticación (debería dar 401)
    try:
        response = requests.get(f"{base_url}/tasks/", timeout=5)
        print(f"✅ Endpoint /tasks/ responde: {response.status_code}")
        if response.status_code == 401:
            print("✅ Autenticación requerida (esperado)")
    except requests.exceptions.RequestException as e:
        print(f"❌ Error en endpoint /tasks/: {e}")
        return False
    
    # 3. Simular datos de tarea como los que envía el frontend
    task_data = {
        "minutes": 120,
        "total_time": 120,
        "start_time": datetime.now().isoformat(),
        "end_time": (datetime.now() + timedelta(minutes=120)).isoformat(),
        "teamIds": [str(uuid.uuid4())],  # UUID ficticio
        "programming_id": str(uuid.uuid4()),  # UUID ficticio
        "code_id": str(uuid.uuid4()),  # UUID ficticio
        "lote": "TEST001",
        "quantity": 100,
        "specification": "Test specification",
        "activity": "TEST ACTIVITY",
        "description": "Test task description"
    }
    
    print(f"📋 Datos de prueba preparados: {json.dumps(task_data, indent=2)}")
    
    # 4. Intentar crear tarea (debería fallar por autenticación, pero nos dirá si el endpoint funciona)
    try:
        print("🚀 Enviando petición POST a /tasks/...")
        response = requests.post(
            f"{base_url}/tasks/", 
            json=task_data,
            timeout=15,  # Timeout más largo para debug
            headers={"Content-Type": "application/json"}
        )
        
        print(f"📊 Respuesta del servidor:")
        print(f"   Status Code: {response.status_code}")
        print(f"   Headers: {dict(response.headers)}")
        
        if response.text:
            try:
                response_json = response.json()
                print(f"   Body: {json.dumps(response_json, indent=2)}")
            except:
                print(f"   Body (raw): {response.text}")
        
        # Analizar el resultado
        if response.status_code == 401:
            print("✅ Endpoint funciona correctamente (requiere autenticación)")
            return True
        elif response.status_code == 422:
            print("✅ Endpoint funciona (error de validación esperado)")
            return True
        elif response.status_code == 500:
            print("❌ Error interno del servidor")
            return False
        else:
            print(f"⚠️ Respuesta inesperada: {response.status_code}")
            return True
            
    except requests.exceptions.Timeout:
        print("❌ TIMEOUT: El servidor no responde en 15 segundos")
        print("   Esto podría explicar el Network Error en el frontend")
        return False
    except requests.exceptions.ConnectionError as e:
        print(f"❌ ERROR DE CONEXIÓN: {e}")
        print("   El servidor puede estar caído o no accesible")
        return False
    except requests.exceptions.RequestException as e:
        print(f"❌ ERROR DE REQUEST: {e}")
        return False

def test_response_time():
    """Prueba el tiempo de respuesta del servidor"""
    
    base_url = "http://localhost:8000/api/v1"
    
    print("\n⏱️ Probando tiempo de respuesta...")
    
    try:
        start_time = datetime.now()
        response = requests.get(f"{base_url}/", timeout=30)
        end_time = datetime.now()
        
        response_time = (end_time - start_time).total_seconds()
        print(f"✅ Tiempo de respuesta: {response_time:.2f} segundos")
        
        if response_time > 10:
            print("⚠️ Tiempo de respuesta alto (>10s) - puede causar timeouts")
        elif response_time > 5:
            print("⚠️ Tiempo de respuesta moderado (>5s)")
        else:
            print("✅ Tiempo de respuesta bueno (<5s)")
            
        return response_time < 10
        
    except requests.exceptions.Timeout:
        print("❌ TIMEOUT: El servidor no responde en 30 segundos")
        return False
    except Exception as e:
        print(f"❌ Error midiendo tiempo de respuesta: {e}")
        return False

def main():
    """Función principal de diagnóstico"""
    print("🔧 DIAGNÓSTICO: Network Error al crear tareas")
    print("=" * 60)
    
    # Verificar que el servidor esté corriendo
    print("1. Verificando conectividad y endpoint...")
    endpoint_ok = test_task_creation_endpoint()
    
    print("\n2. Verificando tiempo de respuesta...")
    response_time_ok = test_response_time()
    
    print("\n" + "=" * 60)
    print("📊 RESUMEN DEL DIAGNÓSTICO:")
    
    if endpoint_ok and response_time_ok:
        print("✅ El backend parece estar funcionando correctamente")
        print("\n💡 POSIBLES CAUSAS DEL NETWORK ERROR:")
        print("   1. Problema de CORS en el navegador")
        print("   2. Timeout específico en el proceso de creación de tareas")
        print("   3. Error después de crear la tarea (en servicios adicionales)")
        print("   4. Problema de autenticación que se resuelve al recargar")
        print("\n🔧 RECOMENDACIONES:")
        print("   1. Revisar logs del servidor durante la creación de tareas")
        print("   2. Verificar la consola del navegador para errores CORS")
        print("   3. Probar con timeout más largo en el frontend")
        print("   4. Revisar servicios que se ejecutan después de crear la tarea")
    elif endpoint_ok and not response_time_ok:
        print("⚠️ El endpoint funciona pero el servidor es lento")
        print("\n🔧 RECOMENDACIONES:")
        print("   1. Aumentar el timeout en el frontend (>10s)")
        print("   2. Optimizar el proceso de creación de tareas")
        print("   3. Revisar la base de datos y consultas lentas")
    elif not endpoint_ok:
        print("❌ Hay problemas con el endpoint de creación de tareas")
        print("\n🔧 RECOMENDACIONES:")
        print("   1. Revisar logs del servidor")
        print("   2. Verificar que el servidor esté corriendo correctamente")
        print("   3. Probar reiniciar el servidor")
    
    return 0

if __name__ == "__main__":
    exit(main())