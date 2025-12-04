"""
Script para marcar todas las programaciones de domingo como NO disponibles.
Los domingos NO se deben programar según las reglas del negocio.
"""
from app.shared.db.session import get_db
from app.modules.programming.models.programming import Programming
from app.modules.programming.models.state import ProgrammingStatus

def mark_all_sundays_unavailable():
    """
    Marca todas las programaciones de domingo como unavailable.
    Los domingos NO tienen horario de programación.
    """
    db = next(get_db())
    
    try:
        # Obtener todas las programaciones
        all_programmings = db.query(Programming).all()
        
        updated_count = 0
        for prog in all_programmings:
            # Si es domingo (weekday 6)
            if prog.date.weekday() == 6:
                if prog.status != ProgrammingStatus.unavailable:
                    print(f"Marcando como unavailable: {prog.id} - {prog.date} (Sunday)")
                    prog.status = ProgrammingStatus.unavailable
                    updated_count += 1
        
        db.commit()
        print(f"\n✅ Total programaciones de domingo marcadas como unavailable: {updated_count}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    mark_all_sundays_unavailable()
