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
        Cambia de 'pendiente' a 'programada' si el lote de la tarea corresponde a una orden.
        """
        if not task.lote or task.lote == '-':
            return
            
        try:
            lote_int = int(task.lote)
            order = db.query(Order).filter(Order.lote == lote_int).first()
            if order and order.status == OrderStatus.pending:
                order.status = OrderStatus.programada
                db.commit()
        except (ValueError, TypeError):
            # Si el lote no es un número válido, no hacer nada
            pass
    
    @staticmethod
    def update_order_status_for_task_deletion(db: Session, task: Task) -> None:
        """
        Actualiza el estado de la orden cuando se elimina una tarea.
        Cambia de 'programada' o 'en progreso' a 'pendiente' si no hay otras tareas para ese lote.
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
            
            # Si no hay más tareas para este lote, cambiar estado a pendiente
            if remaining_tasks == 0 and order.status in [OrderStatus.programada, OrderStatus.in_progress]:
                order.status = OrderStatus.pending
                db.commit()
        except (ValueError, TypeError):
            # Si el lote no es un número válido, no hacer nada
            pass
    
    @staticmethod
    def update_order_status_for_task_start(db: Session, programming_task: ProgrammingTask) -> None:
        """
        Actualiza el estado de la orden cuando se inicia una tarea.
        Cambia de 'pendiente' o 'programada' a 'en progreso' si la tarea se ejecuta hoy.
        """
        task = programming_task.task
        if not task or not task.lote or task.lote == '-':
            return
            
        try:
            lote_int = int(task.lote)
            order = db.query(Order).filter(Order.lote == lote_int).first()
            if not order:
                return
                
            # Verificar si la tarea se ejecuta hoy
            today = datetime.now().date()
            task_date = None
            
            # Obtener la fecha de la tarea desde la programación
            if programming_task.start_time:
                task_date = programming_task.start_time.date()
            elif programming_task.programming:
                task_date = programming_task.programming.date
                
            # Si la tarea se ejecuta hoy y el estado es pendiente o programada, cambiar a en progreso
            if task_date == today and order.status in [OrderStatus.pending, OrderStatus.programada]:
                order.status = OrderStatus.in_progress
                db.commit()
        except (ValueError, TypeError):
            # Si el lote no es un número válido, no hacer nada
            pass

    @staticmethod
    def update_order_status_for_programming_date(db: Session, programming_task: ProgrammingTask) -> None:
        """
        Actualiza el estado de la orden cuando la fecha de programación coincide con hoy.
        Cambia de 'pendiente' o 'programada' a 'en progreso' automáticamente.
        """
        task = programming_task.task
        if not task or not task.lote or task.lote == '-':
            return
            
        try:
            lote_int = int(task.lote)
            order = db.query(Order).filter(Order.lote == lote_int).first()
            if not order:
                return
                
            # Verificar si la programación es para hoy
            today = datetime.now().date()
            programming_date = programming_task.programming.date
                
            # Si la programación es para hoy y el estado es pendiente o programada, cambiar a en progreso
            if programming_date == today and order.status in [OrderStatus.pending, OrderStatus.programada]:
                order.status = OrderStatus.in_progress
                db.commit()
        except (ValueError, TypeError):
            # Si el lote no es un número válido, no hacer nada
            pass
    
    @staticmethod
    def update_order_status_for_task_completion(db: Session, programming_task: ProgrammingTask) -> None:
        """
        Actualiza el estado de la orden cuando se completa una tarea.
        Cambia a 'completada' si la tarea se marca como completada.
        """
        task = programming_task.task
        if not task or not task.lote or task.lote == '-':
            return
            
        try:
            lote_int = int(task.lote)
            order = db.query(Order).filter(Order.lote == lote_int).first()
            if not order:
                return
                
            if programming_task.is_completed:
                order.status = OrderStatus.completed
            else:
                # Si se desmarca como completada, determinar el estado correcto
                today = datetime.now().date()
                task_date = None
                
                if programming_task.start_time:
                    task_date = programming_task.start_time.date()
                elif programming_task.programming:
                    task_date = programming_task.programming.date
                    
                if task_date == today:
                    order.status = OrderStatus.in_progress
                else:
                    order.status = OrderStatus.programada
                    
            db.commit()
        except (ValueError, TypeError):
            # Si el lote no es un número válido, no hacer nada
            pass
    
    @staticmethod
    def update_order_status_for_task_reprogramming(db: Session, programming_task: ProgrammingTask, new_date: date) -> None:
        """
        Actualiza el estado de la orden cuando se reprograma una tarea.
        Cambia de 'en progreso' a 'programada' si la tarea se reprograma para otro día.
        """
        task = programming_task.task
        if not task or not task.lote or task.lote == '-':
            return
            
        try:
            lote_int = int(task.lote)
            order = db.query(Order).filter(Order.lote == lote_int).first()
            if not order:
                return
                
            today = datetime.now().date()
            
            # Si la tarea estaba en progreso y se reprograma para otro día
            if order.status == OrderStatus.in_progress and new_date != today:
                order.status = OrderStatus.programada
                db.commit()
        except (ValueError, TypeError):
            # Si el lote no es un número válido, no hacer nada
            pass
    
    @staticmethod
    def sync_order_status_for_lote(db: Session, lote: str) -> None:
        """
        Sincroniza el estado de una orden basándose en el estado actual de todas sus tareas.
        Útil para casos donde se necesita recalcular el estado correcto.
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
                # Si no hay tareas, estado pendiente
                order.status = OrderStatus.pending
                db.commit()
                return
                
            # Verificar si hay tareas completadas
            completed_tasks = []
            in_progress_tasks = []
            programmed_tasks = []
            
            for task in tasks:
                # Obtener las programaciones de la tarea
                programming_tasks = db.query(ProgrammingTask).filter(
                    ProgrammingTask.task_id == task.id
                ).all()
                
                for pt in programming_tasks:
                    if pt.is_completed:
                        completed_tasks.append(pt)
                    elif pt.real_start_time:
                        in_progress_tasks.append(pt)
                    else:
                        programmed_tasks.append(pt)
            
            # Determinar el estado basado en las tareas
            if completed_tasks:
                order.status = OrderStatus.completed
            elif in_progress_tasks:
                order.status = OrderStatus.in_progress
            elif programmed_tasks:
                # Verificar si alguna tarea programada se ejecuta hoy
                today = datetime.now().date()
                has_today_task = False
                for pt in programmed_tasks:
                    task_date = None
                    if pt.start_time:
                        task_date = pt.start_time.date()
                    elif pt.programming:
                        task_date = pt.programming.date
                    
                    if task_date == today:
                        has_today_task = True
                        break
                
                if has_today_task:
                    order.status = OrderStatus.in_progress
                else:
                    order.status = OrderStatus.programada
            else:
                order.status = OrderStatus.pending
                
            db.commit()
        except (ValueError, TypeError):
            # Si el lote no es un número válido, no hacer nada
            pass
