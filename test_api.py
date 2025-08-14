#!/usr/bin/env python3
"""
Script para probar la API de códigos
"""

import requests

# URL base de la API
BASE_URL = "http://localhost:8000/api/v1"

def test_codes_api():
    print("Probando API de códigos...")
    
    # 1. Probar obtener todos los códigos
    try:
        response = requests.get(f"{BASE_URL}/codes")
        print(f"GET /codes - Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"Total códigos: {data.get('total', 0)}")
            if data.get('codes'):
                print("Primeros códigos:")
                for code in data['codes'][:3]:
                    print(f"  - {code.get('code')}: {code.get('description')}")
        else:
            print(f"Error: {response.text}")
    except Exception as e:
        print(f"Error conectando a la API: {e}")
        return
    
    # 2. Probar buscar un código específico
    test_code = "F136-B"
    try:
        response = requests.get(f"{BASE_URL}/codes/by_code/{test_code}/activity")
        print(f"\nGET /codes/by_code/{test_code}/activity - Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"Código: {data.get('code')}")
            print(f"Total actividades: {data.get('total_activities')}")
            for activity in data.get('activities', []):
                print(f"  - Actividad: {activity.get('activity')}")
        else:
            print(f"Error: {response.text}")
    except Exception as e:
        print(f"Error: {e}")
    
    # 3. Probar buscar con parámetros de búsqueda
    try:
        response = requests.get(f"{BASE_URL}/codes?search={test_code}")
        print(f"\nGET /codes?search={test_code} - Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"Total códigos encontrados: {data.get('total', 0)}")
            for code in data.get('codes', []):
                print(f"  - {code.get('code')}: {code.get('activity')}")
        else:
            print(f"Error: {response.text}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_codes_api() 