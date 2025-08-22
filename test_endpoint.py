#!/usr/bin/env python3
"""
Script para probar el endpoint de programaciones disponibles por equipo
"""
import requests
import json
from datetime import date

def test_available_programmings_endpoint():
    """Prueba el endpoint de programaciones disponibles"""
    
    # Configuración
    base_url = "http://localhost:8000"
    endpoint = "/api/v1/programmings/team/{team_uuid}/available"
    
    # Token de ejemplo (necesitarás un token válido)
    token = "YOUR_JWT_TOKEN_HERE"
    
    # UUID de ejemplo (necesitarás un UUID válido de un equipo)
    team_uuid = "123e4567-e89b-12d3-a456-426614174000"
    
    # Headers
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    # URL completa
    url = f"{base_url}{endpoint.format(team_uuid=team_uuid)}"
    
    print(f"Probando endpoint: {url}")
    print(f"Headers: {json.dumps(headers, indent=2)}")
    print("-" * 50)
    
    try:
        # Hacer la petición
        response = requests.get(url, headers=headers)
        
        print(f"Status Code: {response.status_code}")
        print(f"Response Headers: {dict(response.headers)}")
        print("-" * 50)
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Respuesta exitosa:")
            print(json.dumps(data, indent=2, ensure_ascii=False))
            
            # Verificar estructura de respuesta
            required_fields = ["team_id", "team_name", "available_programmings"]
            for field in required_fields:
                if field in data:
                    print(f"✅ Campo '{field}' presente")
                else:
                    print(f"❌ Campo '{field}' faltante")
            
            # Verificar programaciones
            programmings = data.get("available_programmings", [])
            print(f"📊 Número de programaciones disponibles: {len(programmings)}")
            
            for i, prog in enumerate(programmings, 1):
                print(f"  Programación {i}:")
                print(f"    ID: {prog.get('id', 'N/A')}")
                print(f"    Equipo: {prog.get('team_name', 'N/A')}")
                print(f"    Fecha: {prog.get('date', 'N/A')}")
                
        elif response.status_code == 401:
            print("❌ Error de autenticación - Token inválido o faltante")
            print("Asegúrate de proporcionar un token JWT válido")
            
        elif response.status_code == 403:
            print("❌ Error de autorización - No tienes permisos para acceder a este equipo")
            
        elif response.status_code == 404:
            print("❌ Equipo no encontrado")
            print("Verifica que el UUID del equipo sea correcto")
            
        else:
            print(f"❌ Error inesperado: {response.status_code}")
            print(f"Respuesta: {response.text}")
            
    except requests.exceptions.ConnectionError:
        print("❌ Error de conexión")
        print("Asegúrate de que el servidor esté ejecutándose en http://localhost:8000")
        
    except Exception as e:
        print(f"❌ Error inesperado: {e}")

def test_without_token():
    """Prueba el endpoint sin token para verificar autenticación"""
    
    base_url = "http://localhost:8000"
    team_uuid = "123e4567-e89b-12d3-a456-426614174000"
    endpoint = f"/api/v1/programmings/team/{team_uuid}/available"
    
    print(f"\n🔒 Probando sin token: {base_url}{endpoint}")
    print("-" * 50)
    
    try:
        response = requests.get(f"{base_url}{endpoint}")
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 401:
            print("✅ Correcto: Endpoint requiere autenticación")
        else:
            print(f"⚠️  Inesperado: Status code {response.status_code}")
            print(f"Respuesta: {response.text}")
            
    except requests.exceptions.ConnectionError:
        print("❌ Error de conexión - Servidor no disponible")

if __name__ == "__main__":
    print("🧪 Pruebas del Endpoint de Programaciones Disponibles")
    print("=" * 60)
    
    # Probar sin token
    test_without_token()
    
    # Probar con token (necesitarás configurar un token válido)
    print("\n" + "=" * 60)
    print("📝 Para probar con autenticación, edita el script y configura:")
    print("1. Un token JWT válido")
    print("2. Un UUID de equipo válido")
    print("3. Ejecuta el servidor con: python -m uvicorn app.main:app --reload")
    print("=" * 60)
    
    # test_available_programmings_endpoint()
