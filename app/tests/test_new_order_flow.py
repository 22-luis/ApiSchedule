"""
Script de prueba para verificar el nuevo flujo GRANULAR de estados de órdenes.

Flujo esperado:
1. Orden creada -> estado: unprogrammed
2. Tarea de Pesado creada y completada -> estado: weighed
3. Tarea de Fabricación creada y completada -> estado: manufactured
4. Tarea de Empaque creada y completada -> estado: packaged
5. Entrega de orden -> estado: delivered
"""

import sys
import os
# Add project root to python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.shared.db.session import SessionLocal
from app.modules.core.models.user import User
from app.modules.core.models.team import Team
from app.modules.codes.models.code import Code
from app.modules.codes.models.preparation import Preparation
from app.modules.programming.models.programming import Programming, ProgrammingTask
from app.modules.programming.models.task import Task
from app.modules.programming.models.order import Order
from app.modules.programming.models.state import OrderStatus, TaskStatus
from app.shared.utils.business.order_status_service import OrderStatusService
from datetime import datetime, date
from sqlalchemy.orm import Session

def create_and_complete_task(db, order_lote, activity, programming_id):
    """Helper para crear y completar una tarea"""
    task = Task(
        lote=str(order_lote),
        description=f"Tarea de {activity}",
        activity=activity,
        quantity=100,
        performance=1.0,
        duration=60
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    
    # Crear ProgrammingTask
    prog_task = ProgrammingTask(
        programming_id=programming_id,
        task_id=task.id,
        order=1,
        is_completed=True  # Marcar como completada directamente
    )
    db.add(prog_task)
    db.commit()
    db.refresh(prog_task)
    
    return task, prog_task

def test_granular_flow():
    db: Session = SessionLocal()
    lote_test = 88888
    
    try:
        print("\n=== PRUEBA DEL FLUJO GRANULAR (Weighed -> Manufactured -> Packaged) ===\n")
        
        # Limpiar datos previos si existen
        existing = db.query(Order).filter(Order.lote == lote_test).first()
        if existing:
            # Eliminar tareas asociadas primero
            tasks = db.query(Task).filter(Task.lote == str(lote_test)).all()
            for t in tasks:
                db.query(ProgrammingTask).filter(ProgrammingTask.task_id == t.id).delete()
                db.delete(t)
            db.delete(existing)
            db.commit()

        # 1. Crear Orden
        print("1. Creando orden nueva...")
        order = Order(
            lote=lote_test,
            code="TEST-FLOW",
            description="Orden de prueba flujo",
            quantity=100,
            bin=8,
            dueDate=date.today(),
            status=OrderStatus.unprogrammed
        )
        db.add(order)
        db.commit()
        
        # Crear una programación dummy para asociar tareas
        programming = Programming(team_id=1, date=date.today())
        db.add(programming)
        db.commit()
        
        print(f"   ✓ Orden creada. Estado inicial: {order.status}")
        assert order.status == OrderStatus.unprogrammed
        
        # 2. Ciclo de PESADO
        print("\n2. Probando ciclo PESADO...")
        task_weighing, prog_task_weighing = create_and_complete_task(db, lote_test, "PESADO", programming.id)
        
        # Actualizar estado
        OrderStatusService.update_order_status_for_task_completion(db, prog_task_weighing)
        db.refresh(order)
        
        print(f"   ✓ Tarea PESADO completada. Estado actual: {order.status}")
        assert order.status == OrderStatus.weighed, f"Esperado: weighed, Actual: {order.status}"
        
        # 3. Ciclo de FABRICACIÓN
        print("\n3. Probando ciclo FABRICACIÓN...")
        task_fab, prog_task_fab = create_and_complete_task(db, lote_test, "MEZCLA EN MAQUINA", programming.id)
        
        # Actualizar estado
        OrderStatusService.update_order_status_for_task_completion(db, prog_task_fab)
        db.refresh(order)
        
        print(f"   ✓ Tarea FABRICACIÓN completada. Estado actual: {order.status}")
        assert order.status == OrderStatus.manufactured, f"Esperado: manufactured, Actual: {order.status}"
        
        # 4. Ciclo de EMPAQUE
        print("\n4. Probando ciclo EMPAQUE...")
        task_pack, prog_task_pack = create_and_complete_task(db, lote_test, "EMPAQUE", programming.id)
        
        # Actualizar estado
        OrderStatusService.update_order_status_for_task_completion(db, prog_task_pack)
        db.refresh(order)
        
        print(f"   ✓ Tarea EMPAQUE completada. Estado actual: {order.status}")
        assert order.status == OrderStatus.packaged, f"Esperado: packaged, Actual: {order.status}"
        
        print("\n=== PRUEBA EXITOSA: El flujo se completó correctamente ===")
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Limpieza
        try:
            if 'order' in locals():
                db.delete(order)
            if 'programming' in locals():
                db.delete(programming)
            # Las tareas se borrarían en cascada o manualmente si fuera necesario, 
            # pero para prueba rápida dejamos que la DB se encargue o lo ignoramos en dev
            db.commit()
        except:
            pass
        db.close()

if __name__ == "__main__":
    test_granular_flow()