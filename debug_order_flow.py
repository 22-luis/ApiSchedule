#!/usr/bin/env python3
"""
Script de diagnóstico para el flujo de órdenes.
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

def test_database_connection():
    """Prueba la conexión a la base de datos"""
    token = get_auth_token()
    if not token:
        return False
    
    headers = {"Authorization": f"Bearer {token}"}
    
    try:
        response = requests.get(f"{BASE_URL}/orders/debug/database_connection", headers=headers)
        
        if response.status_code == 200:
            result = response.json()
            print("✅ Conexión a base de datos OK")
            print(f"   - Órdenes en BD: {result.get('orders_count', 'N/A')}")
            return True
        else:
            print(f"❌ Error en conexión BD: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Error probando conexión: {e}")
        return False

def test_order_status_update():
    """Prueba la actualización de estado de una orden existente"""
    token = get_auth_token()
    if not token:
        return False
    
    headers = {"Authorization": f"Bearer {token}"}
    
    try:
        # Primero obtener una orden existente
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
        
        # Probar cambio de estado
        new_status = "manufactured" if current_status != "manufactured" else "programmed"
        
        response = requests.post(
            f"{BASE_URL}/orders/debug/test_order_update/{order_lote}",
            params={"new_status": new_status},
            headers=headers
        )
        
        if response.status_code == 200:
            result = response.json()
            if result.get("success"):
                print(f"✅ Actualización de estado exitosa: {result['previous_status']} → {result['new_status']}")
                return True
            else:
                print(f"❌ Error en actualización: {result.get('error')}")
                return False
        else:
            print(f"❌ Error HTTP: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Error probando actualización: {e}")
        return False

def main():
    """Ejecuta las pruebas de diagnóstico"""
    print("🔍 DIAGNÓSTICO DEL SISTEMA DE ÓRDENES")
    print("=" * 50)
    
    # Probar conexión al servidor
    print("\n1. Probando conexión al servidor...")
    token = get_auth_token()
    if not token:
        print("❌ No se pudo conectar al servidor. Verifica que esté ejecutándose.")
        return
    
    print("✅ Conexión al servidor OK")
    
    # Probar conexión a BD
    print("\n2. Probando conexión a base de datos...")
    db_ok = test_database_connection()
    
    if not db_ok:
        print("❌ Problema con la base de datos")
        return
    
    # Probar actualización de estado
    print("\n3. Probando actualización de estado...")
    update_ok = test_order_status_update()
    
    # Resumen
    print("\n" + "=" * 50)
    print("📊 RESUMEN:")
    print(f"   Servidor: ✅ OK")
    print(f"   Base de datos: {'✅ OK' if db_ok else '❌ ERROR'}")
    print(f"   Actualización de estado: {'✅ OK' if update_ok else '❌ ERROR'}")
    
    if db_ok and update_ok:
        print("\n🎯 Sistema funcionando correctamente")
    else:
        print("\n⚠️ Hay problemas que necesitan atención")

if __name__ == "__main__":
    main()