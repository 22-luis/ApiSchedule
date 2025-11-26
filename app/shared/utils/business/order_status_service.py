from sqlalchemy.orm import Session
from app.modules.programming.models.order import Order
from app.modules.programming.models.task import Task
from app.modules.programming.models.programming import ProgrammingTask
from app.modules.programming.models.state import OrderStatus, TaskStatus
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
    def _are_all_tasks_completed_for_activity(db: Session, lote: str, activity_keywords: list[str]) -> bool:
        """
        Verifica si todas las tareas relacionadas con ciertas palabras clave de actividad están completadas.
        Retorna True si existen tareas y todas están completadas.
        Retorna False si no existen tareas o si alguna no está completada.
        """
        tasks = db.query(Task).join(ProgrammingTask).filter(Task.lote == lote).all()
        
        relevant_tasks = []
        for task in tasks:
            if not task.activity:
                continue
            activity_upper = task.activity.upper()
            if any(keyword in activity_upper for keyword in activity_keywords):
                relevant_tasks.append(task)
        
        if not relevant_tasks:
            return False
            
        # Verificar si todas las tareas relevantes están completadas
        # Una tarea se considera completada si tiene al menos un ProgrammingTask con estado COMPLETED (o is_completed=True)
        for task in relevant_tasks:
            # Verificar si alguna programación de esta tarea está completada
            is_task_completed = False
            for prog_task in task.programming_tasks:
                if prog_task.is_completed:
                    is_task_completed = True
                    break
            
            if not is_task_completed:
                return False
                
        return True

    @staticmethod
    def update_order_status_for_task_completion(db: Session, programming_task: ProgrammingTask) -> None:
        """
        Actualiza el estado de la orden basándose en la etapa más avanzada completada.
        Jerarquía: Empacada > Fabricada > Pesada
        """
        task = programming_task.task
        if not task or not task.lote or task.lote == '-':
            return
            
        try:
            lote_int = int(task.lote)
            order = db.query(Order).filter(Order.lote == lote_int).first()
            if not order:
                return
            
            # Si la orden ya está entregada o completada, no retroceder automáticamente
            if order.status in [OrderStatus.delivered, OrderStatus.completed]:
                return

            lote_str = str(lote_int)
            
            # 1. Verificar Empaque (Estado: packaged)
            # Palabras clave: EMPAQUE, ENCAJADO, ETIQUETADO, PALETIZADO
            packaging_keywords = ["EMPAQUE", "ENCAJADO", "ETIQUETADO", "PALETIZADO"]
            if OrderStatusService._are_all_tasks_completed_for_activity(db, lote_str, packaging_keywords):
                if order.status != OrderStatus.packaged:
                    order.status = OrderStatus.packaged
                    db.commit()
                return

            # 2. Verificar Fabricación (Estado: manufactured)
            # Palabras clave: FABRICADO, MEZCLA, MOLIENDA, COCCCION
            fabrication_keywords = ["FABRICADO", "MEZCLA", "MOLIENDA", "COCCION", "FABICACION"]
            if OrderStatusService._are_all_tasks_completed_for_activity(db, lote_str, fabrication_keywords):
                if order.status != OrderStatus.manufactured:
                    order.status = OrderStatus.manufactured
                    db.commit()
                return

            # 3. Verificar Pesado (Estado: weighed)
            # Palabras clave: PESADO
            weighing_keywords = ["PESADO"]
            if OrderStatusService._are_all_tasks_completed_for_activity(db, lote_str, weighing_keywords):
                if order.status != OrderStatus.weighed:
                    order.status = OrderStatus.weighed
                    db.commit()
                return
                
            # Si no se cumple ninguno de los anteriores, mantener estado actual (o programmed/pending)
            # No forzamos cambio aquí para no interferir con estados manuales como 'pending'
                
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
            from app.modules.programming.models.programming import Programming
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
