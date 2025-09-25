#!/usr/bin/env python3
"""
Script de prueba para verificar que las órdenes en estado 'pending' puedan ser entregadas.
"""

import requests
import json

BASE_URL = "http://localhost:8000/api/v1"

def test_pending_order_delivery():
    """Prueba que las órdenes en estado 'pending' puedan ser entregadas."""
    
    print("🧪 Probando entrega de órdenes en estado 'pending'...")
    
    # Datos de prueba para login
    login_data = {
        "username": "admin",  # Ajustar según tu configuración
        "password": "admin123"  # Ajustar según tu configuración
    }
    
    try:
        # 1. Hacer login para obtener token
        print("1. Intentando hacer login...")
        login_response = requests.post(f"{BASE_URL}/auth/login", json=login_data)
        
        if login_response.status_code != 200:
            print(f"❌ Error en login: {login_response.status_code}")
            print(f"   Respuesta: {login_response.text}")
            return
        
        token = login_response.json().get("access_token")
        headers = {"Authorization": f"Bearer {token}"}
        print("✅ Login exitoso")
        
        # 2. Buscar una orden en estado 'pending'
        print("2. Buscando órdenes en estado 'pending'...")
        orders_response = requests.get(f"{BASE_URL}/orders/?status=pending", headers=headers)
        
        if orders_response.status_code != 200:
            print(f"❌ Error obteniendo órdenes: {orders_response.status_code}")
            return
        
        orders_data = orders_response.json()
        orders = orders_data.get("orders", [])
        
        if not orders:
            print("⚠️  No se encontraron órdenes en estado 'pending'")
            print("   Creando una orden de prueba...")
            
            # Crear una orden de prueba
            test_order = {
                "lote": 99999,
                "code": "TEST_PENDING",
                "description": "Orden de prueba para entrega en estado pending",
                "quantity": 100,
                "bin": 999,
                "dueDate": "2025-01-01T00:00:00"
            }
            
            create_response = requests.post(f"{BASE_URL}/orders/", 
                                          json=test_order, 
                                          headers=headers)
            
            if create_response.status_code != 200:
                print(f"❌ Error creando orden de prueba: {create_response.status_code}")
                return
            
            print("✅ Orden de prueba creada")
            order_lote = test_order["lote"]
        else:
            order_lote = orders[0]["lote"]
            print(f"✅ Encontrada orden en estado 'pending': {order_lote}")
        
        # 3. Intentar entregar la orden
        print(f"3. Intentando entregar orden {order_lote}...")
        delivery_data = {"delivered_quantity": 50}
        
        delivery_response = requests.post(f"{BASE_URL}/orders/{order_lote}/deliver", 
                                        json=delivery_data, 
                                        headers=headers)
        
        if delivery_response.status_code == 200:
            print("✅ ¡Entrega exitosa! Las órdenes 'pending' ahora pueden ser entregadas")
            result = delivery_response.json()
            print(f"   Estado después de entrega: {result.get('status')}")
            print(f"   Cantidad entregada: {result.get('delivered_quantity')}")
            print(f"   Cantidad faltante: {result.get('missing_quantity')}")
        else:
            print(f"❌ Error en entrega: {delivery_response.status_code}")
            print(f"   Respuesta: {delivery_response.text}")
            
    except Exception as e:
        print(f"❌ Error durante la prueba: {e}")

if __name__ == "__main__":
    test_pending_order_delivery()