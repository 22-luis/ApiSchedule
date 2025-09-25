#!/usr/bin/env python3
"""
Script rápido para verificar si el servidor está funcionando
"""

import requests
import json

def test_server():
    """Prueba si el servidor está funcionando"""
    try:
        # Probar endpoint de health
        response = requests.get("http://localhost:8000/health", timeout=5)
        if response.status_code == 200:
            print("✅ Servidor funcionando correctamente")
            print(f"   Health check: {response.json()}")
            return True
        else:
            print(f"❌ Servidor respondió con status {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print("❌ No se puede conectar al servidor. ¿Está ejecutándose?")
        return False
    except Exception as e:
        print(f"❌ Error conectando al servidor: {e}")
        return False

def test_auth_endpoint():
    """Prueba el endpoint de autenticación"""
    try:
        response = requests.get("http://localhost:8000/api/v1/auth/login", timeout=5)
        print(f"🔐 Endpoint de auth disponible: {response.status_code}")
        return True
    except Exception as e:
        print(f"❌ Error en endpoint de auth: {e}")
        return False

def main():
    print("🚀 PRUEBA RÁPIDA DEL SERVIDOR")
    print("=" * 40)
    
    # 1. Verificar servidor
    if not test_server():
        print("\n💡 Para iniciar el servidor, ejecuta:")
        print("   python start.py")
        return
    
    # 2. Verificar endpoint de auth
    test_auth_endpoint()
    
    print("\n✅ Servidor listo para pruebas")

if __name__ == "__main__":
    main()
