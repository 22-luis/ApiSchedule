"""
Script para verificar las tareas del viernes 5 de diciembre de 2025
"""
import sys
sys.path.append('.')

from datetime import date
from app.shared.db.session import SessionLocal
from app.modules.programming.models.programming import Programming, ProgrammingTask
from app.modules.programming.models.task import Task

def check_friday_tasks():
    db = SessionLocal()
    try:
        friday_date = date(2025, 12, 5)
        
        # Buscar la programación del viernes
        programming = db.query(Programming).filter(
            Programming.date == friday_date
        ).first()
        
        if not programming:
            print(f"❌ No hay programación para {friday_date}")
            return
        
        print(f"✅ Programación encontrada:")
        print(f"   ID: {programming.id}")
        print(f"   Fecha: {programming.date}")
        print(f"   Status: {programming.status}")
        print(f"   Team ID: {programming.team_id}")
        print()
        
        # Buscar las tareas de esa programación
        programming_tasks = db.query(ProgrammingTask).filter(
            ProgrammingTask.programming_id == programming.id
        ).order_by(ProgrammingTask.start_time).all()
        
        print(f"📋 Tareas encontradas: {len(programming_tasks)}")
        print()
        
        for i, pt in enumerate(programming_tasks, 1):
            task = db.query(Task).filter(Task.id == pt.task_id).first()
            if task:
                print(f"{i}. Lote {task.lote}:")
                print(f"   Start: {pt.start_time}")
                print(f"   End: {pt.end_time}")
                print(f"   Duration: {task.minutes} min")
                print(f"   Order: {pt.order}")
                print()
        
        # Calcular el tiempo final
        if programming_tasks:
            last_task = max(programming_tasks, key=lambda x: x.end_time if x.end_time else x.start_time)
            if last_task.end_time:
                end_minutes = last_task.end_time.hour * 60 + last_task.end_time.minute
                print(f"⏰ Última tarea termina a las {last_task.end_time.strftime('%H:%M')} ({end_minutes} minutos)")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    check_friday_tasks()
