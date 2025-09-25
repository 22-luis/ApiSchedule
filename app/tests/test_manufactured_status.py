#!/usr/bin/env python3
"""
Script para probar que el estado 'manufactured' funciona correctamente.
"""
import requests
import json

BASE_URL = "http://localhost:8000/api/v1"

def get_auth_token():
    """Obtiene el token de autenticación"""
    try:
        login_data = {
            "username": "ADMIN",
            "password": "h33r#M91"
        }
        
        response = requests.post(f"{BASE_URL}/auth/login", data=login_data)
        if response.status_code == 200:
            return response.json()["access_token"]
        else:
            print(f"❌ Error en login: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        print(f"❌ Error conectando al servidor: {e}")
        return None

def test_manufactured_status():
    """Prueba actualizar una orden al estado 'manufactured'"""
    token = get_auth_token()
    if not token:
        return False
    
    headers = {"Authorization": f"Bearer {token}"}
    
    try:
        # Obtener la primera orden disponible
        response = requests.get(f"{BASE_URL}/orders/?limit=1", headers=headers)
        
        if response.status_code != 200:
            print(f"❌ No se pudieron obtener órdenes: {response.status_code}")
            return False
        
        orders_data = response.json()
        if not orders_data.get("orders"):
            print("⚠️ No hay órdenes en la base de datos para probar")
            return False
        
        order = orders_data["orders"][0]
        order_lote = order["lote"]
        current_status = order["status"]
        
        print(f"📋 Probando con orden {order_lote} (estado actual: {current_status})")
        
        # Intentar cambiar a 'manufactured'
        update_data = {"status": "manufactured"}
        
        response = requests.patch(
            f"{BASE_URL}/orders/{order_lote}/status",
            json=update_data,
            headers=headers
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Estado actualizado exitosamente a: {result.get('status')}")
            return True
        else:
            print(f"❌ Error actualizando estado: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Error en la prueba: {e}")
        return False

def main():
    """Ejecuta la prueba"""
    print("🧪 PROBANDO ESTADO 'MANUFACTURED'")
    print("=" * 40)
    
    success = test_manufactured_status()
    
    print("\n" + "=" * 40)
    if success:
        print("🎯 ✅ El estado 'manufactured' funciona correctamente")
    else:
        print("🎯 ❌ Hay problemas con el estado 'manufactured'")

if __name__ == "__main__":
    main()