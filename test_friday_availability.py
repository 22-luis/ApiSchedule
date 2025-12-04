"""
Script de prueba para verificar que la disponibilidad del viernes se detecte correctamente.
"""
from app.shared.db.session import SessionLocal
from app.shared.db.session import SessionLocal
# Import models in correct order to avoid Mapper errors
from app.modules.programming.models.task import Task
from app.modules.programming.models.programming import Programming, ProgrammingTask
from app.shared.utils.business.programming_availability import restore_programmings_availability
from datetime import date

def test_friday_availability():
    """
    Prueba la función restore_programmings_availability con el viernes 12/05/2025
    """
    db = SessionLocal()
    
    try:
        # Buscar la programación del viernes
        friday_prog = db.query(Programming).filter(
            Programming.date == date(2025, 12, 5)
        ).first()
        
        if friday_prog:
            print(f"Programación encontrada: {friday_prog.id}")
            print(f"Fecha: {friday_prog.date}")
            print(f"Estado actual: {friday_prog.status}")
            print(f"Team ID: {friday_prog.team_id}")
            print("\nEjecutando restore_programmings_availability...")
            
            # Ejecutar la función de restauración
            result = restore_programmings_availability(db)
            
            print(f"\n✅ Resultados:")
            print(f"  - Total programaciones: {result['total_programmings']}")
            print(f"  - Restauradas a available: {result['restored_to_available']}")
            print(f"  - Marcadas unavailable: {result['marked_unavailable']}")
            print(f"  - Sin cambios: {result['already_correct']}")
            
            # Refrescar y mostrar el estado final del viernes
            db.refresh(friday_prog)
            print(f"\nEstado final del viernes: {friday_prog.status}")
        else:
            print("❌ No se encontró programación para el viernes 12/05/2025")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    test_friday_availability()
