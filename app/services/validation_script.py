"""
Script de validación para verificar que la migración a servicios refactorizados funciona correctamente.
"""

import sys
import os
from typing import Dict, Any, List
from datetime import datetime

# Agregar el directorio raíz al path para imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from app.services.factory import TaskServiceFactory
from app.services.config import ServiceType, ServiceConfig


def validate_factory_creation() -> Dict[str, Any]:
    """
    Valida que el factory puede crear servicios correctamente.
    
    Returns:
        Resultado de la validación
    """
    print("🔧 Validando Factory Pattern...")
    
    results = {
        "success": True,
        "errors": [],
        "warnings": [],
        "services_created": []
    }
    
    try:
        # Validar creación de servicio de pesado
        weighing_service = TaskServiceFactory.create_weighing_service()
        if weighing_service:
            results["services_created"].append("WeighingTaskService")
            print("✅ WeighingTaskService creado exitosamente")
        else:
            results["errors"].append("No se pudo crear WeighingTaskService")
            results["success"] = False
            print("❌ Error al crear WeighingTaskService")
        
        # Validar creación de servicio de fabricación
        fabrication_service = TaskServiceFactory.create_fabrication_service()
        if fabrication_service:
            results["services_created"].append("FabricationTaskService")
            print("✅ FabricationTaskService creado exitosamente")
        else:
            results["errors"].append("No se pudo crear FabricationTaskService")
            results["success"] = False
            print("❌ Error al crear FabricationTaskService")
        
        # Validar creación genérica
        weighing_service_generic = TaskServiceFactory.create_service(ServiceType.WEIGHING)
        if weighing_service_generic:
            print("✅ WeighingTaskService creado genéricamente")
        else:
            results["errors"].append("No se pudo crear WeighingTaskService genéricamente")
            results["success"] = False
            print("❌ Error al crear WeighingTaskService genéricamente")
        
        fabrication_service_generic = TaskServiceFactory.create_service(ServiceType.FABRICATION)
        if fabrication_service_generic:
            print("✅ FabricationTaskService creado genéricamente")
        else:
            results["errors"].append("No se pudo crear FabricationTaskService genéricamente")
            results["success"] = False
            print("❌ Error al crear FabricationTaskService genéricamente")
        
        # Validar servicio no implementado
        packaging_service = TaskServiceFactory.create_service(ServiceType.PACKAGING)
        if packaging_service is None:
            print("✅ PackagingService correctamente no implementado")
        else:
            results["warnings"].append("PackagingService no debería estar implementado aún")
            print("⚠️ PackagingService inesperadamente implementado")
        
    except Exception as e:
        results["errors"].append(f"Error en validación de factory: {str(e)}")
        results["success"] = False
        print(f"❌ Error en validación de factory: {str(e)}")
    
    return results


def validate_service_configuration() -> Dict[str, Any]:
    """
    Valida que la configuración de servicios funciona correctamente.
    
    Returns:
        Resultado de la validación
    """
    print("\n⚙️ Validando Configuración de Servicios...")
    
    results = {
        "success": True,
        "errors": [],
        "warnings": [],
        "configs_validated": []
    }
    
    try:
        # Validar configuración de pesado
        weighing_config = ServiceConfig.get_config(ServiceType.WEIGHING)
        if weighing_config:
            results["configs_validated"].append("WeighingConfig")
            print("✅ Configuración de pesado válida")
            
            # Validar límite de tiempo
            time_limit = ServiceConfig.get_time_limit(ServiceType.WEIGHING)
            if time_limit:
                print(f"✅ Límite de tiempo de pesado: {time_limit}")
            else:
                results["errors"].append("No se pudo obtener límite de tiempo de pesado")
                results["success"] = False
                print("❌ Error al obtener límite de tiempo de pesado")
            
            # Validar palabras clave
            keywords = ServiceConfig.get_activity_keywords(ServiceType.WEIGHING)
            if keywords:
                print(f"✅ Palabras clave de pesado: {keywords}")
            else:
                results["errors"].append("No se pudo obtener palabras clave de pesado")
                results["success"] = False
                print("❌ Error al obtener palabras clave de pesado")
        else:
            results["errors"].append("No se pudo obtener configuración de pesado")
            results["success"] = False
            print("❌ Error al obtener configuración de pesado")
        
        # Validar configuración de fabricación
        fabrication_config = ServiceConfig.get_config(ServiceType.FABRICATION)
        if fabrication_config:
            results["configs_validated"].append("FabricationConfig")
            print("✅ Configuración de fabricación válida")
            
            # Validar límite de tiempo
            time_limit = ServiceConfig.get_time_limit(ServiceType.FABRICATION)
            if time_limit:
                print(f"✅ Límite de tiempo de fabricación: {time_limit}")
            else:
                results["errors"].append("No se pudo obtener límite de tiempo de fabricación")
                results["success"] = False
                print("❌ Error al obtener límite de tiempo de fabricación")
            
            # Validar palabras clave
            keywords = ServiceConfig.get_activity_keywords(ServiceType.FABRICATION)
            if keywords:
                print(f"✅ Palabras clave de fabricación: {keywords}")
            else:
                results["errors"].append("No se pudo obtener palabras clave de fabricación")
                results["success"] = False
                print("❌ Error al obtener palabras clave de fabricación")
        else:
            results["errors"].append("No se pudo obtener configuración de fabricación")
            results["success"] = False
            print("❌ Error al obtener configuración de fabricación")
        
    except Exception as e:
        results["errors"].append(f"Error en validación de configuración: {str(e)}")
        results["success"] = False
        print(f"❌ Error en validación de configuración: {str(e)}")
    
    return results


def validate_service_information() -> Dict[str, Any]:
    """
    Valida que la información de servicios funciona correctamente.
    
    Returns:
        Resultado de la validación
    """
    print("\n📊 Validando Información de Servicios...")
    
    results = {
        "success": True,
        "errors": [],
        "warnings": [],
        "services_info": []
    }
    
    try:
        # Obtener servicios disponibles
        available_services = TaskServiceFactory.get_available_services()
        if available_services:
            print(f"✅ Servicios disponibles: {[s.value for s in available_services]}")
            results["services_info"].extend([s.value for s in available_services])
        else:
            results["errors"].append("No se pudieron obtener servicios disponibles")
            results["success"] = False
            print("❌ Error al obtener servicios disponibles")
        
        # Validar información de cada servicio
        for service_type in available_services:
            service_info = TaskServiceFactory.get_service_info(service_type)
            if service_info:
                print(f"✅ Información de {service_type.value}: {service_info}")
                results["services_info"].append(service_info)
            else:
                results["errors"].append(f"No se pudo obtener información de {service_type.value}")
                results["success"] = False
                print(f"❌ Error al obtener información de {service_type.value}")
        
    except Exception as e:
        results["errors"].append(f"Error en validación de información: {str(e)}")
        results["success"] = False
        print(f"❌ Error en validación de información: {str(e)}")
    
    return results


def validate_imports() -> Dict[str, Any]:
    """
    Valida que todos los imports necesarios funcionan correctamente.
    
    Returns:
        Resultado de la validación
    """
    print("\n📦 Validando Imports...")
    
    results = {
        "success": True,
        "errors": [],
        "warnings": [],
        "imports_validated": []
    }
    
    try:
        # Validar imports de servicios refactorizados
        from app.services.weighing_task_service import WeighingTaskService
        results["imports_validated"].append("WeighingTaskService")
        print("✅ Import de WeighingTaskService exitoso")
        
        from app.services.fabrication_task_service import FabricationTaskService
        results["imports_validated"].append("FabricationTaskService")
        print("✅ Import de FabricationTaskService exitoso")
        
        from app.services.base_task_service import BaseTaskService
        results["imports_validated"].append("BaseTaskService")
        print("✅ Import de BaseTaskService exitoso")
        
        from app.services.utils.programming_utils import ProgrammingUtils
        results["imports_validated"].append("ProgrammingUtils")
        print("✅ Import de ProgrammingUtils exitoso")
        
        from app.services.utils.team_selection_service import TeamSelectionService
        results["imports_validated"].append("TeamSelectionService")
        print("✅ Import de TeamSelectionService exitoso")
        
    except ImportError as e:
        results["errors"].append(f"Error de import: {str(e)}")
        results["success"] = False
        print(f"❌ Error de import: {str(e)}")
    except Exception as e:
        results["errors"].append(f"Error inesperado en imports: {str(e)}")
        results["success"] = False
        print(f"❌ Error inesperado en imports: {str(e)}")
    
    return results


def run_full_validation() -> Dict[str, Any]:
    """
    Ejecuta todas las validaciones.
    
    Returns:
        Resultado completo de todas las validaciones
    """
    print("🚀 Iniciando Validación Completa de Servicios Refactorizados")
    print("=" * 60)
    
    start_time = datetime.now()
    
    # Ejecutar todas las validaciones
    factory_results = validate_factory_creation()
    config_results = validate_service_configuration()
    info_results = validate_service_information()
    import_results = validate_imports()
    
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    
    # Consolidar resultados
    all_success = all([
        factory_results["success"],
        config_results["success"],
        info_results["success"],
        import_results["success"]
    ])
    
    all_errors = []
    all_warnings = []
    
    for results in [factory_results, config_results, info_results, import_results]:
        all_errors.extend(results.get("errors", []))
        all_warnings.extend(results.get("warnings", []))
    
    final_results = {
        "success": all_success,
        "duration_seconds": duration,
        "errors": all_errors,
        "warnings": all_warnings,
        "summary": {
            "factory_validation": factory_results["success"],
            "config_validation": config_results["success"],
            "info_validation": info_results["success"],
            "import_validation": import_results["success"]
        },
        "details": {
            "factory": factory_results,
            "config": config_results,
            "info": info_results,
            "imports": import_results
        }
    }
    
    # Mostrar resumen
    print("\n" + "=" * 60)
    print("📋 RESUMEN DE VALIDACIÓN")
    print("=" * 60)
    
    if final_results["success"]:
        print("🎉 ¡TODAS LAS VALIDACIONES EXITOSAS!")
    else:
        print("❌ ALGUNAS VALIDACIONES FALLARON")
    
    print(f"⏱️ Duración: {duration:.2f} segundos")
    print(f"❌ Errores: {len(all_errors)}")
    print(f"⚠️ Advertencias: {len(all_warnings)}")
    
    if all_errors:
        print("\n📝 Errores encontrados:")
        for i, error in enumerate(all_errors, 1):
            print(f"  {i}. {error}")
    
    if all_warnings:
        print("\n⚠️ Advertencias encontradas:")
        for i, warning in enumerate(all_warnings, 1):
            print(f"  {i}. {warning}")
    
    print("\n" + "=" * 60)
    
    return final_results


if __name__ == "__main__":
    # Ejecutar validación completa
    results = run_full_validation()
    
    # Salir con código de error si hay fallos
    if not results["success"]:
        sys.exit(1)
    else:
        print("✅ Validación completada exitosamente")
        sys.exit(0)
