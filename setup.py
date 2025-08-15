#!/usr/bin/env python3
"""
Script de configuración para ApiSchedule.
Ayuda a configurar el entorno y las dependencias.
"""
import os
import sys
import subprocess
import shutil
from pathlib import Path

def run_command(command, description):
    """Ejecuta un comando y maneja errores"""
    print(f"🔄 {description}...")
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        print(f"✅ {description} completado")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Error en {description}: {e}")
        print(f"   Comando: {command}")
        print(f"   Salida: {e.stdout}")
        print(f"   Error: {e.stderr}")
        return False

def check_python_version():
    """Verifica la versión de Python"""
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 8):
        print("❌ Se requiere Python 3.8 o superior")
        print(f"   Versión actual: {version.major}.{version.minor}.{version.micro}")
        return False
    print(f"✅ Python {version.major}.{version.minor}.{version.micro} - OK")
    return True

def create_env_file():
    """Crea el archivo .env si no existe"""
    env_file = Path(".env")
    if env_file.exists():
        print("✅ Archivo .env ya existe")
        return True
    
    env_example = Path("env.example")
    if env_example.exists():
        shutil.copy(env_example, env_file)
        print("✅ Archivo .env creado desde env.example")
        print("⚠️  IMPORTANTE: Edita el archivo .env con tus configuraciones")
        return True
    else:
        print("❌ No se encontró env.example")
        return False

def install_dependencies():
    """Instala las dependencias de Python"""
    if not run_command("pip install -r requirements.txt", "Instalando dependencias"):
        return False
    
    # Verificar instalación de pydantic-settings
    try:
        import pydantic_settings
        print("✅ pydantic-settings instalado correctamente")
    except ImportError:
        print("❌ Error: pydantic-settings no se instaló correctamente")
        print("   Intentando instalar manualmente...")
        if not run_command("pip install pydantic-settings", "Instalando pydantic-settings"):
            return False
    
    return True

def create_directories():
    """Crea directorios necesarios"""
    directories = ["logs", "uploads"]
    for directory in directories:
        Path(directory).mkdir(exist_ok=True)
        print(f"✅ Directorio {directory} creado/verificado")

def check_database_connection():
    """Verifica la conexión a la base de datos"""
    print("🔄 Verificando conexión a base de datos...")
    
    # Verificar si PostgreSQL está instalado
    if not shutil.which("psql"):
        print("⚠️  PostgreSQL no encontrado en PATH")
        print("   Asegúrate de tener PostgreSQL instalado y configurado")
        return False
    
    # Intentar conectar usando las variables de entorno
    try:
        from app.core.config_simple import settings
        print(f"   Usuario: {settings.POSTGRES_USER}")
        print(f"   Base de datos: {settings.POSTGRES_DB}")
        print(f"   Servidor: {settings.POSTGRES_SERVER}:{settings.POSTGRES_PORT}")
        
        # Aquí podrías agregar una verificación real de conexión
        print("✅ Configuración de base de datos detectada")
        return True
    except Exception as e:
        print(f"❌ Error verificando configuración de base de datos: {e}")
        return False

def main():
    """Función principal del script"""
    print("🚀 Configurando ApiSchedule...")
    print("=" * 50)
    
    # Verificar Python
    if not check_python_version():
        sys.exit(1)
    
    # Crear archivo .env
    if not create_env_file():
        print("⚠️  Continúa manualmente creando el archivo .env")
    
    # Instalar dependencias
    if not install_dependencies():
        print("❌ Error instalando dependencias")
        sys.exit(1)
    
    # Crear directorios
    create_directories()
    
    # Verificar base de datos
    check_database_connection()
    
    print("\n" + "=" * 50)
    print("✅ Configuración completada")
    print("\n📋 Próximos pasos:")
    print("1. Edita el archivo .env con tus configuraciones")
    print("2. Configura tu base de datos PostgreSQL")
    print("3. Ejecuta las migraciones: alembic upgrade head")
    print("4. Inicia la aplicación: uvicorn app.main:app --reload")
    print("\n📚 Documentación:")
    print("- README.md - Guía principal")
    print("- API_DOCUMENTATION.md - Documentación de la API")
    print("- /docs - Documentación interactiva (cuando la app esté corriendo)")

if __name__ == "__main__":
    main()
