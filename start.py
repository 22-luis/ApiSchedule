#!/usr/bin/env python3
"""
Script de inicio rápido para ApiSchedule.
Facilita la ejecución de la aplicación con configuración automática.
"""
import os
import sys
import subprocess
from pathlib import Path

def check_env_file():
    """Verifica si existe el archivo .env"""
    env_file = Path(".env")
    if not env_file.exists():
        print("⚠️  No se encontró el archivo .env")
        print("   Creando archivo .env desde env.example...")
        
        env_example = Path("env.example")
        if env_example.exists():
            import shutil
            shutil.copy(env_example, env_file)
            print("✅ Archivo .env creado")
            print("⚠️  IMPORTANTE: Edita el archivo .env con tus configuraciones antes de continuar")
            return False
        else:
            print("❌ No se encontró env.example")
            return False
    
    return True

def check_dependencies():
    """Verifica que las dependencias estén instaladas"""
    try:
        import fastapi
        import uvicorn
        import pydantic
        print("✅ Dependencias principales verificadas")
        return True
    except ImportError as e:
        print(f"❌ Dependencias faltantes: {e}")
        print("   Ejecuta: pip install -r requirements.txt")
        return False

def start_application():
    """Inicia la aplicación"""
    print("🚀 Iniciando ApiSchedule...")
    
    # Verificar archivo .env
    if not check_env_file():
        print("\n📋 Pasos para continuar:")
        print("1. Edita el archivo .env con tus configuraciones")
        print("2. Ejecuta este script nuevamente")
        return False
    
    # Verificar dependencias
    if not check_dependencies():
        return False
    
    # Iniciar la aplicación
    try:
        print("🔄 Iniciando servidor...")
        subprocess.run([
            sys.executable, "-m", "uvicorn", 
            "app.main:app", 
            "--reload", 
            "--host", "0.0.0.0", 
            "--port", "8000"
        ], check=True)
    except KeyboardInterrupt:
        print("\n👋 Aplicación detenida por el usuario")
    except subprocess.CalledProcessError as e:
        print(f"❌ Error iniciando la aplicación: {e}")
        return False
    
    return True

def main():
    """Función principal"""
    print("=" * 50)
    print("🚀 ApiSchedule - Inicio Rápido")
    print("=" * 50)
    
    if start_application():
        print("✅ Aplicación iniciada correctamente")
    else:
        print("❌ Error iniciando la aplicación")
        sys.exit(1)

if __name__ == "__main__":
    main()
