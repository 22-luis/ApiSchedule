#!/usr/bin/env python3
"""
Script para ejecutar tests de ApiSchedule de manera fácil.
"""
import sys
import subprocess
import argparse
from pathlib import Path

def run_command(command, description):
    """Ejecuta un comando y maneja errores."""
    print(f"\n🔄 {description}...")
    print(f"Comando: {' '.join(command)}")
    
    try:
        result = subprocess.run(command, check=True, capture_output=True, text=True)
        print(f"✅ {description} completado exitosamente")
        if result.stdout:
            print(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Error en {description}")
        print(f"Error: {e}")
        if e.stdout:
            print("Salida estándar:")
            print(e.stdout)
        if e.stderr:
            print("Error estándar:")
            print(e.stderr)
        return False

def main():
    parser = argparse.ArgumentParser(description="Ejecutar tests de ApiSchedule")
    parser.add_argument(
        "--type", 
        choices=["all", "auth", "users", "teams", "tasks", "programming", "orders", "utils"],
        default="all",
        help="Tipo de tests a ejecutar"
    )
    parser.add_argument(
        "--coverage", 
        action="store_true",
        help="Generar reporte de cobertura"
    )
    parser.add_argument(
        "--verbose", 
        action="store_true",
        help="Ejecutar con salida verbose"
    )
    parser.add_argument(
        "--html", 
        action="store_true",
        help="Generar reporte HTML de cobertura"
    )
    parser.add_argument(
        "--fast", 
        action="store_true",
        help="Ejecutar tests rápidos (excluir tests lentos)"
    )
    
    args = parser.parse_args()
    
    # Verificar que estamos en el directorio correcto
    if not Path("app").exists() or not Path("requirements.txt").exists():
        print("❌ Error: Debes ejecutar este script desde el directorio raíz del proyecto")
        sys.exit(1)
    
    # Construir comando pytest
    cmd = ["python", "-m", "pytest"]
    
    # Agregar opciones según argumentos
    if args.verbose:
        cmd.append("-v")
    
    if args.coverage:
        cmd.extend(["--cov=app", "--cov-report=term-missing"])
    
    if args.html:
        cmd.extend(["--cov=app", "--cov-report=html", "--cov-report=term-missing"])
    
    if args.fast:
        cmd.extend(["-m", "not slow"])
    
    # Agregar tipo de test específico
    if args.type != "all":
        if args.type == "auth":
            cmd.append("app/tests/test_auth.py")
        elif args.type == "users":
            cmd.append("app/tests/test_users.py")
        elif args.type == "teams":
            cmd.append("app/tests/test_teams.py")
        elif args.type == "tasks":
            cmd.append("app/tests/test_tasks.py")
        elif args.type == "programming":
            cmd.append("app/tests/test_programming.py")
        elif args.type == "orders":
            cmd.append("app/tests/test_orders.py")
        elif args.type == "utils":
            cmd.append("app/tests/test_utils.py")
    
    # Ejecutar tests
    print("🚀 Iniciando tests de ApiSchedule")
    print(f"📁 Directorio: {Path.cwd()}")
    print(f"🎯 Tipo: {args.type}")
    
    success = run_command(cmd, f"Ejecutando tests de {args.type}")
    
    if success:
        print("\n🎉 ¡Todos los tests completados exitosamente!")
        if args.html:
            print("📊 Reporte HTML de cobertura generado en: htmlcov/index.html")
    else:
        print("\n💥 Algunos tests fallaron")
        sys.exit(1)

if __name__ == "__main__":
    main()
