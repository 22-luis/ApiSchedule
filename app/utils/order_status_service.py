from sqlalchemy.orm import Session
from app.models.order import Order
from app.models.task import Task
from app.models.programming import ProgrammingTask
from app.models.state import OrderStatus
from datetime import datetime, date
from typing import Optional


class OrderStatusService:
    """Servicio para manejar los cambios de estado de las órdenes de manera centralizada"""
    
    @staticmethod
    def update_order_status_for_task_creation(db: Session, task: Task) -> None:
        """
        Actualiza el estado de la orden cuando se crea una tarea.
        Cambia de 'unprogrammed' a 'programmed' si el lote de la tarea corresponde a una orden.
        """
        if not task.lote or task.lote == '-':
            return
            
        try:
            lote_int = int(task.lote)
            order = db.query(Order).filter(Order.lote == lote_int).first()
            if order and order.status == OrderStatus.unprogrammed:
                order.status = OrderStatus.programmed
                db.commit()
        except (ValueError, TypeError):
            # Si el lote no es un número válido, no hacer nada
            pass
    
    @staticmethod
    def update_order_status_based_on_missing_quantity(db: Session, order: Order) -> None:
        """
        Actualiza el estado de la orden basándose en la cantidad faltante.
        Si missing_quantity > 0: cambia a 'pending'
        Si missing_quantity <= 0: cambia a 'completed'
        """
        if order.missing_quantity is None:
            return
            
        if order.missing_quantity > 0 and order.status == OrderStatus.programmed:
            order.status = OrderStatus.pending
            db.commit()
        elif order.missing_quantity <= 0 and order.status == OrderStatus.pending:
            order.status = OrderStatus.completed
            db.commit()
    
    @staticmethod
    def update_order_status_for_task_deletion(db: Session, task: Task) -> None:
        """
        Actualiza el estado de la orden cuando se elimina una tarea.
        Cambia de 'programmed' a 'unprogrammed' si no hay otras tareas para ese lote.
        """
        if not task.lote or task.lote == '-':
            return
            
        try:
            lote_int = int(task.lote)
            order = db.query(Order).filter(Order.lote == lote_int).first()
            if not order:
                return
                
            # Verificar si hay otras tareas para este lote
            remaining_tasks = db.query(Task).filter(
                Task.lote == task.lote,
                Task.id != task.id
            ).count()
            
            # Si no hay más tareas para este lote, cambiar estado a unprogrammed
            if remaining_tasks == 0 and order.status == OrderStatus.programmed:
                order.status = OrderStatus.unprogrammed
                db.commit()
        except (ValueError, TypeError):
            # Si el lote no es un número válido, no hacer nada
            pass
    
    @staticmethod
    def update_order_status_for_task_start(db: Session, programming_task: ProgrammingTask) -> None:
        """
        Actualiza el estado de la orden cuando se inicia una tarea.
        Cambia de 'programmed' a 'pending' cuando una tarea comienza su ejecución.
        """
        task = programming_task.task
        if not task or not task.lote or task.lote == '-':
            return
            
        try:
            lote_int = int(task.lote)
            order = db.query(Order).filter(Order.lote == lote_int).first()
            if not order:
                return
                
            pass
                
        except (ValueError, TypeError):
            # Si el lote no es un número válido, no hacer nada
            pass
    
    @staticmethod
    def update_order_status_for_task_completion(db: Session, programming_task: ProgrammingTask) -> None:
        """
        Actualiza el estado de la orden cuando se completa una tarea.
        Si la tarea completada tiene una actividad de empaque, cambia el estado a 'manufactured'.
        Los procesos de pesado y fabricado no cambian el estado de la orden.
        """
        task = programming_task.task
        if not task or not task.lote or task.lote == '-':
            print(f"[DEBUG] No se puede procesar tarea: task={task}, lote={task.lote if task else None}")
            return
            
        try:
            lote_int = int(task.lote)
            order = db.query(Order).filter(Order.lote == lote_int).first()
            if not order:
                print(f"[DEBUG] No se encontró orden con lote {lote_int}")
                return
                
            print(f"[DEBUG] Procesando tarea completada para orden {order.lote}, estado actual: {order.status}")
            print(f"[DEBUG] Tarea completada: {programming_task.is_completed}")
            
            # Solo procesar si la tarea está marcada como completada
            if programming_task.is_completed:
                
                pass
            else:
                print(f"[DEBUG] Tarea no está marcada como completada")
                
        except (ValueError, TypeError) as e:
            print(f"[DEBUG] Error procesando lote {task.lote}: {e}")
        except Exception as e:
            print(f"[DEBUG] Error inesperado actualizando estado de orden: {e}")
            db.rollback()
            raise
    
    @staticmethod
    def update_order_status_for_programming_date(db: Session, programming_task: ProgrammingTask) -> None:
        """
        Actualiza el estado de la orden cuando se programa una tarea para una fecha específica.
        Si la programación es para hoy y la orden está en estado 'programmed', 
        automáticamente la cambia a 'pending'.
        """
        task = programming_task.task
        if not task or not task.lote or task.lote == '-':
            return
            
        try:
            lote_int = int(task.lote)
            order = db.query(Order).filter(Order.lote == lote_int).first()
            if not order:
                return
                
            # Obtener la fecha de la programación
            from app.models.programming import Programming
            programming = db.query(Programming).filter(Programming.id == programming_task.programming_id).first()
            if not programming:
                return
                
            # Si la programación es para hoy y la orden está programmed, cambiar a pending
            today = date.today()
            if programming.date == today and order.status == OrderStatus.programmed:
                order.status = OrderStatus.pending
                db.commit()
                
        except (ValueError, TypeError):
            # Si el lote no es un número válido, no hacer nada
            pass
    
    @staticmethod
    def sync_order_status_for_lote(db: Session, lote: str) -> None:
        """
        Sincroniza el estado de una orden basándose en el nuevo flujo:
        1. Sin tareas: unprogrammed
        2. Con tareas: programmed
        3. Si missing_quantity > 0: pending
        4. Si missing_quantity <= 0: completed
        """
        if not lote or lote == '-':
            return
            
        try:
            lote_int = int(lote)
            order = db.query(Order).filter(Order.lote == lote_int).first()
            if not order:
                return
                
            # Obtener todas las tareas para este lote
            tasks = db.query(Task).filter(Task.lote == lote).all()
            
            if not tasks:
                # Si no hay tareas, estado unprogrammed
                order.status = OrderStatus.unprogrammed
            else:
                # Si hay tareas, estado programmed
                order.status = OrderStatus.programmed
                
                # Verificar missing_quantity para determinar si debe ser pending o completed
                if order.missing_quantity is not None:
                    if order.missing_quantity > 0:
                        order.status = OrderStatus.pending
                    elif order.missing_quantity <= 0:
                        order.status = OrderStatus.completed
                
            db.commit()
        except (ValueError, TypeError):
            # Si el lote no es un número válido, no hacer nada
            pass
