#!/usr/bin/env python3
"""
Script de prueba para verificar el flujo completo de estados de órdenes.
"""
import requests
import json
from datetime import datetime

# Configuración
BASE_URL = "http://localhost:8000/api/v1"
USERNAME = "ADMIN"
PASSWORD = "h33r#M91"

def get_auth_token():
    """Obtiene el token de autenticación"""
    login_data = {
        "username": USERNAME,
        "password": PASSWORD
    }
    
    response = requests.post(f"{BASE_URL}/auth/login", data=login_data)
    if response.status_code == 200:
        return response.json()["access_token"]
    else:
        print(f"Error en login: {response.status_code} - {response.text}")
        return None

def test_order_creation():
    """Prueba la creación de una orden con estado inicial correcto"""
    token = get_auth_token()
    if not token:
        return False
    
    headers = {"Authorization": f"Bearer {token}"}
    
    # Crear una orden de prueba
    test_order = {
        "lote": 99999,
        "code": "TEST001",
        "description": "Orden de prueba para flujo de estados",
        "quantity": 100,
        "bin": 1,
        "dueDate": datetime.now().isoformat()
    }
    
    print("1. Creando orden de prueba...")
    response = requests.post(f"{BASE_URL}/orders/", json=test_order, headers=headers)
    
    if response.status_code == 200:
        result = response.json()
        print(f"✅ Orden creada exitosamente")
        
        # Verificar que el estado inicial sea 'unprogrammed'
        if result["created_orders"]:
            order_status = result["created_orders"][0]["status"]
            if order_status == "unprogrammed":
                print(f"✅ Estado inicial correcto: {order_status}")
                return True
            else:
                print(f"❌ Estado inicial incorrecto: {order_status} (esperado: unprogrammed)")
                return False
    else:
        print(f"❌ Error creando orden: {response.status_code} - {response.text}")
        return False

def test_task_creation_status_change():
    """Prueba que al crear una tarea con lote, la orden cambie a 'programmed'"""
    token = get_auth_token()
    if not token:
        return False
    
    headers = {"Authorization": f"Bearer {token}"}
    
    print("\n2. Verificando cambio de estado al crear tarea...")
    
    # Verificar el estado actual de la orden
    response = requests.get(f"{BASE_URL}/orders/test_order_flow/99999", headers=headers)
    if response.status_code == 200:
        result = response.json()
        print(f"Estado actual de la orden: {result['order']['status']}")
        
        if result['tasks_count'] > 0:
            print(f"✅ La orden tiene {result['tasks_count']} tareas asociadas")
            
            # Verificar si alguna tarea tiene lote 99999
            has_matching_lote = any(task['lote'] == '99999' for task in result['tasks'])
            if has_matching_lote and result['order']['status'] == 'programmed':
                print("✅ Estado cambió correctamente a 'programmed' al tener tareas")
                return True
            elif has_matching_lote:
                print(f"⚠️ Hay tareas con el lote pero el estado es: {result['order']['status']}")
                return False
            else:
                print("⚠️ No hay tareas con el lote de la orden")
                return False
        else:
            print("⚠️ La orden no tiene tareas asociadas aún")
            return False
    else:
        print(f"❌ Error verificando orden: {response.status_code} - {response.text}")
        return False

def test_packaging_completion():
    """Prueba que al completar una tarea de empaque, la orden cambie a 'manufactured'"""
    token = get_auth_token()
    if not token:
        return False
    
    headers = {"Authorization": f"Bearer {token}"}
    
    print("\n3. Probando completación de tarea de empaque...")
    
    response = requests.post(f"{BASE_URL}/orders/test_packaging_completion/99999", headers=headers)
    
    if response.status_code == 200:
        result = response.json()
        print(f"Resultado: {json.dumps(result, indent=2)}")
        
        if result.get("success") and result.get("status_changed"):
            print(f"✅ Estado cambió correctamente de {result['previous_status']} a {result['new_status']}")
            return True
        elif result.get("success"):
            print(f"⚠️ Tarea completada pero estado no cambió: {result['new_status']}")
            return False
        else:
            print(f"❌ Error en la prueba: {result.get('error', 'Error desconocido')}")
            return False
    else:
        print(f"❌ Error en prueba de empaque: {response.status_code} - {response.text}")
        return False

def cleanup_test_order():
    """Limpia la orden de prueba"""
    token = get_auth_token()
    if not token:
        return
    
    headers = {"Authorization": f"Bearer {token}"}
    
    print("\n4. Limpiando orden de prueba...")
    response = requests.delete(f"{BASE_URL}/orders/99999", headers=headers)
    
    if response.status_code == 200:
        print("✅ Orden de prueba eliminada")
    else:
        print(f"⚠️ No se pudo eliminar la orden de prueba: {response.status_code}")

def main():
    """Ejecuta todas las pruebas"""
    print("🧪 Iniciando pruebas del flujo de estados de órdenes")
    print("=" * 60)
    
    # Ejecutar pruebas
    test1_passed = test_order_creation()
    test2_passed = test_task_creation_status_change()
    test3_passed = test_packaging_completion()
    
    # Limpiar
    cleanup_test_order()
    
    # Resumen
    print("\n" + "=" * 60)
    print("📊 RESUMEN DE PRUEBAS:")
    print(f"1. Creación con estado inicial correcto: {'✅ PASS' if test1_passed else '❌ FAIL'}")
    print(f"2. Cambio a 'programmed' con tareas: {'✅ PASS' if test2_passed else '❌ FAIL'}")
    print(f"3. Cambio a 'manufactured' con empaque: {'✅ PASS' if test3_passed else '❌ FAIL'}")
    
    all_passed = test1_passed and test2_passed and test3_passed
    print(f"\n🎯 RESULTADO GENERAL: {'✅ TODAS LAS PRUEBAS PASARON' if all_passed else '❌ ALGUNAS PRUEBAS FALLARON'}")

if __name__ == "__main__":
    main()