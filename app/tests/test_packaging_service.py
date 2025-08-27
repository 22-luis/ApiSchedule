#!/usr/bin/env python3
"""
Script de prueba para verificar el servicio de empaque.
"""

import sys
import os
from typing import Dict, Any, List

# Agregar el directorio raíz al path para imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.services.factory import TaskServiceFactory
from app.services.config import ServiceType, ServiceConfig
from app.core.enums import PackagingActivities, PackagingTeams


def test_packaging_service_creation():
    """Prueba la creación del servicio de empaque"""
    print("🔧 Probando creación del servicio de empaque...")
    
    try:
        # Crear servicio usando el factory
        packaging_service = TaskServiceFactory.create_packaging_service()
        
        if packaging_service:
            print("✅ Servicio de empaque creado exitosamente")
            print(f"   - Tipo: {type(packaging_service).__name__}")
            print(f"   - Límite de tiempo: {packaging_service.time_limit}")
            print(f"   - Tolerancia: {packaging_service.tolerance_minutes} minutos")
            return True
        else:
            print("❌ No se pudo crear el servicio de empaque")
            return False
            
    except Exception as e:
        print(f"❌ Error al crear servicio de empaque: {str(e)}")
        return False


def test_packaging_configuration():
    """Prueba la configuración del servicio de empaque"""
    print("\n⚙️ Probando configuración del servicio de empaque...")
    
    try:
        # Obtener configuración
        config = ServiceConfig.get_config(ServiceType.PACKAGING)
        
        if config:
            print("✅ Configuración obtenida exitosamente")
            print(f"   - Descripción: {config.get('description')}")
            print(f"   - Límite de tiempo: {config.get('time_limit')}")
            print(f"   - Tolerancia: {config.get('tolerance_minutes')} minutos")
            print(f"   - Palabras clave: {config.get('activity_keywords')}")
            print(f"   - Prioridades de equipos: {config.get('team_priorities')}")
            return True
        else:
            print("❌ No se pudo obtener la configuración")
            return False
            
    except Exception as e:
        print(f"❌ Error al obtener configuración: {str(e)}")
        return False


def test_packaging_enums():
    """Prueba las enumeraciones de empaque"""
    print("\n📋 Probando enumeraciones de empaque...")
    
    try:
        # Verificar actividades de empaque
        print("Actividades de empaque:")
        for activity in PackagingActivities:
            print(f"   - {activity.name}: {activity.value}")
        
        # Verificar equipos de empaque
        print("\nEquipos de empaque:")
        for team in PackagingTeams:
            print(f"   - {team.name}: {team.value}")
        
        print("✅ Enumeraciones verificadas correctamente")
        return True
        
    except Exception as e:
        print(f"❌ Error al verificar enumeraciones: {str(e)}")
        return False


def test_packaging_activity_keywords():
    """Prueba las palabras clave de actividades de empaque"""
    print("\n🔍 Probando palabras clave de actividades de empaque...")
    
    try:
        keywords = ServiceConfig.get_activity_keywords(ServiceType.PACKAGING)
        
        if keywords:
            print("✅ Palabras clave obtenidas:")
            for keyword in keywords:
                print(f"   - {keyword}")
            
            # Verificar que las actividades de empaque coinciden con las palabras clave
            activities = [activity.value for activity in PackagingActivities]
            matches = []
            
            for activity in activities:
                for keyword in keywords:
                    if keyword in activity.upper():
                        matches.append(activity)
                        break
            
            print(f"\nActividades que coinciden con palabras clave: {len(matches)}/{len(activities)}")
            for match in matches:
                print(f"   - {match}")
            
            return True
        else:
            print("❌ No se pudieron obtener las palabras clave")
            return False
            
    except Exception as e:
        print(f"❌ Error al verificar palabras clave: {str(e)}")
        return False


def test_packaging_team_priorities():
    """Prueba las prioridades de equipos de empaque"""
    print("\n🏭 Probando prioridades de equipos de empaque...")
    
    try:
        priorities = ServiceConfig.get_team_priorities(ServiceType.PACKAGING)
        
        if priorities:
            print("✅ Prioridades de equipos obtenidas:")
            for priority in priorities:
                print(f"   - {priority}")
            
            # Verificar que los equipos de empaque coinciden con las prioridades
            teams = [team.value for team in PackagingTeams]
            matches = []
            
            for team in teams:
                for priority in priorities:
                    if priority.lower() in team.lower():
                        matches.append(team)
                        break
            
            print(f"\nEquipos que coinciden con prioridades: {len(matches)}/{len(teams)}")
            for match in matches:
                print(f"   - {match}")
            
            return True
        else:
            print("❌ No se pudieron obtener las prioridades de equipos")
            return False
            
    except Exception as e:
        print(f"❌ Error al verificar prioridades de equipos: {str(e)}")
        return False


def test_packaging_service_info():
    """Prueba la información del servicio de empaque"""
    print("\n📊 Probando información del servicio de empaque...")
    
    try:
        service_info = TaskServiceFactory.get_service_info(ServiceType.PACKAGING)
        
        if service_info:
            print("✅ Información del servicio obtenida:")
            for key, value in service_info.items():
                print(f"   - {key}: {value}")
            return True
        else:
            print("❌ No se pudo obtener la información del servicio")
            return False
            
    except Exception as e:
        print(f"❌ Error al obtener información del servicio: {str(e)}")
        return False


def run_all_tests():
    """Ejecuta todas las pruebas"""
    print("🚀 Iniciando pruebas del servicio de empaque")
    print("=" * 60)
    
    tests = [
        test_packaging_service_creation,
        test_packaging_configuration,
        test_packaging_enums,
        test_packaging_activity_keywords,
        test_packaging_team_priorities,
        test_packaging_service_info
    ]
    
    results = []
    
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            print(f"❌ Error en prueba {test.__name__}: {str(e)}")
            results.append(False)
    
    # Resumen
    print("\n" + "=" * 60)
    print("📋 RESUMEN DE PRUEBAS")
    print("=" * 60)
    
    passed = sum(results)
    total = len(results)
    
    print(f"✅ Pruebas exitosas: {passed}/{total}")
    print(f"❌ Pruebas fallidas: {total - passed}/{total}")
    
    if passed == total:
        print("🎉 ¡TODAS LAS PRUEBAS EXITOSAS!")
        return True
    else:
        print("⚠️ Algunas pruebas fallaron")
        return False


if __name__ == "__main__":
    success = run_all_tests()
    
    if success:
        print("\n✅ Servicio de empaque listo para usar")
        sys.exit(0)
    else:
        print("\n❌ Servicio de empaque necesita correcciones")
        sys.exit(1)
