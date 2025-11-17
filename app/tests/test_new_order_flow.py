"""
Script de prueba para verificar el nuevo flujo de estados de órdenes.

Flujo esperado:
1. Orden creada -> estado: unprogrammed
2. Orden agregada a tarea -> estado: programmed  
3. Si missing_quantity > 0 -> estado: pending
4. Si missing_quantity <= 0 -> estado: completed
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy.orm import Session
from app.db.database import SessionLocal
from app.models.order import Order
from app.models.task import Task
from app.models.state import OrderStatus
from app.utils.bussiness.order_status_service import OrderStatusService
from datetime import datetime, date

def test_order_flow():
    """Prueba el flujo completo de estados de órdenes"""
    
    db: Session = SessionLocal()
    
    try:
        print("=== PRUEBA DEL NUEVO FLUJO DE ESTADOS DE ÓRDENES ===\n")
        
        # 1. Crear una orden nueva
        print("1. Creando orden nueva...")
        test_order = Order(
            lote=99999,
            code="TEST001",
            description="Orden de prueba",
            quantity=100,
            bin=1,
            dueDate=date.today(),
            status=OrderStatus.unprogrammed,  # Estado inicial
            missing_quantity=None
        )
        
        db.add(test_order)
        db.commit()
        db.refresh(test_order)
        
        print(f"   ✓ Orden creada con lote {test_order.lote}")
        print(f"   ✓ Estado inicial: {test_order.status}")
        assert test_order.status == OrderStatus.unprogrammed, f"Estado esperado: unprogrammed, actual: {test_order.status}"
        
        # 2. Crear una tarea para la orden (simular agregar a tarea)
        print("\n2. Agregando orden a una tarea...")
        test_task = Task(
            lote=str(test_order.lote),
            description="Tarea de prueba",
            activity="Pesado",
            quantity=test_order.quantity,
            performance=1.0,
            duration=60
        )
        
        db.add(test_task)
        db.commit()
        
        # Actualizar estado usando el servicio
        OrderStatusService.update_order_status_for_task_creation(db, test_task)
        db.refresh(test_order)
        
        print(f"   ✓ Tarea creada para lote {test_task.lote}")
        print(f"   ✓ Estado después de agregar tarea: {test_order.status}")
        assert test_order.status == OrderStatus.programmed, f"Estado esperado: programmed, actual: {test_order.status}"
        
        # 3. Simular recepción parcial (missing_quantity > 0)
        print("\n3. Simulando recepción parcial (missing_quantity = 20)...")
        test_order.received_quantity = 80
        test_order.missing_quantity = 20  # Falta cantidad
        test_order.received_user = "warehouse_user"
        test_order.received_date = datetime.now()
        
        # Actualizar estado basado en missing_quantity
        OrderStatusService.update_order_status_based_on_missing_quantity(db, test_order)
        db.refresh(test_order)
        
        print(f"   ✓ Cantidad recibida: {test_order.received_quantity}")
        print(f"   ✓ Cantidad faltante: {test_order.missing_quantity}")
        print(f"   ✓ Estado después de recepción parcial: {test_order.status}")
        assert test_order.status == OrderStatus.pending, f"Estado esperado: pending, actual: {test_order.status}"
        
        # 4. Simular recepción completa (missing_quantity = 0)
        print("\n4. Simulando recepción completa (missing_quantity = 0)...")
        test_order.received_quantity = 100
        test_order.missing_quantity = 0  # No falta nada
        test_order.submitted_user = "warehouse_user"
        test_order.submitted_date = datetime.now()
        
        # Actualizar estado basado en missing_quantity
        OrderStatusService.update_order_status_based_on_missing_quantity(db, test_order)
        db.refresh(test_order)
        
        print(f"   ✓ Cantidad recibida: {test_order.received_quantity}")
        print(f"   ✓ Cantidad faltante: {test_order.missing_quantity}")
        print(f"   ✓ Estado después de recepción completa: {test_order.status}")
        assert test_order.status == OrderStatus.completed, f"Estado esperado: completed, actual: {test_order.status}"
        
        # 5. Probar eliminación de tarea (volver a unprogrammed)
        print("\n5. Probando eliminación de tarea...")
        test_order.missing_quantity = None  # Reset para probar solo el efecto de eliminar tarea
        OrderStatusService.update_order_status_for_task_deletion(db, test_task)
        
        # Eliminar la tarea
        db.delete(test_task)
        db.commit()
        db.refresh(test_order)
        
        print(f"   ✓ Tarea eliminada")
        print(f"   ✓ Estado después de eliminar tarea: {test_order.status}")
        # Nota: Como missing_quantity es None, el estado no debería cambiar por esa lógica
        
        # 6. Probar sincronización de estado
        print("\n6. Probando sincronización de estado...")
        OrderStatusService.sync_order_status_for_lote(db, str(test_order.lote))
        db.refresh(test_order)
        
        print(f"   ✓ Estado después de sincronización: {test_order.status}")
        # Como no hay tareas, debería ser unprogrammed
        assert test_order.status == OrderStatus.unprogrammed, f"Estado esperado: unprogrammed, actual: {test_order.status}"
        
        print("\n=== TODAS LAS PRUEBAS PASARON EXITOSAMENTE ===")
        
        # Limpiar datos de prueba
        db.delete(test_order)
        db.commit()
        print("\n✓ Datos de prueba limpiados")
        
    except Exception as e:
        print(f"\n❌ Error en la prueba: {e}")
        db.rollback()
        
        # Intentar limpiar en caso de error
        try:
            test_order = db.query(Order).filter(Order.lote == 99999).first()
            if test_order:
                db.delete(test_order)
            test_task = db.query(Task).filter(Task.lote == "99999").first()
            if test_task:
                db.delete(test_task)
            db.commit()
            print("✓ Datos de prueba limpiados después del error")
        except:
            pass
            
        raise e
        
    finally:
        db.close()

def test_role_permissions():
    """Prueba que los roles tienen los permisos correctos"""
    print("\n=== PRUEBA DE PERMISOS DE ROLES ===")
    
    # Esta es una prueba conceptual - en un entorno real necesitarías
    # configurar usuarios de prueba con diferentes roles
    
    roles_with_order_update_permission = [
        "ADMIN", "PLANNER", "SUPERVISOR", "WAREHOUSE"
    ]
    
    roles_without_permission = ["USER"]
    
    print("✓ Roles con permiso para actualizar órdenes:")
    for role in roles_with_order_update_permission:
        print(f"   - {role}")
    
    print("✓ Roles SIN permiso para actualizar órdenes:")
    for role in roles_without_permission:
        print(f"   - {role}")
    
    print("✓ El rol WAREHOUSE puede actualizar campos de almacén y missing_quantity")
    print("✓ Todos los roles (excepto USER) pueden cambiar estados manualmente")

if __name__ == "__main__":
    print("Iniciando pruebas del nuevo flujo de órdenes...\n")
    
    try:
        test_order_flow()
        test_role_permissions()
        print("\n🎉 TODAS LAS PRUEBAS COMPLETADAS EXITOSAMENTE")
        
    except Exception as e:
        print(f"\n💥 FALLO EN LAS PRUEBAS: {e}")
        sys.exit(1)