import traceback
from datetime import datetime, timezone as dt_timezone
from pytz import timezone
from sqlalchemy.orm import Session, joinedload
from fastapi import HTTPException

from app.modules.programming.models.programming import ProgrammingTask
from app.modules.programming.schemas.programming import ProgrammingTaskReportIn
from app.modules.organization.models.user import User
from app.shared.utils.business.order_status_service import OrderStatusService

class TaskTimerService:
    @staticmethod
    def start_timer(db: Session, task_id: str, current_user: User, data: dict = None, programming_id: str = None):
        """Starts the timer for a specific task in a programming."""
        query = db.query(ProgrammingTask).filter_by(task_id=task_id)
        if programming_id:
            query = query.filter_by(programming_id=programming_id)
        
        pt = query.first()
        if not pt:
            return None, "ProgrammingTask not found"
        
        sv_tz = timezone("America/El_Salvador")
        if data and data.get("real_start_time"):
            val = data["real_start_time"]
            if isinstance(val, str):
                pt.real_start_time = datetime.fromisoformat(val)
            else:
                pt.real_start_time = val
        else:
            pt.real_start_time = datetime.now(sv_tz)
        
        pt.completed_by_user_id = current_user.id
        
        # Actualizar estado de la orden usando el servicio centralizado
        from app.shared.utils.business.order_status_service import OrderStatusService
        OrderStatusService.update_order_status_for_task_start(db, pt)
        
        db.commit()
        db.refresh(pt)
        return pt, None

    @staticmethod
    def stop_timer(db: Session, task_id: str, current_user: User, real_quantity: float = None, programming_id: str = None, data: ProgrammingTaskReportIn = None):
        """Stops the timer and handles auto-completion and order status updates."""
        query = db.query(ProgrammingTask).options(
            joinedload(ProgrammingTask.task)
        ).filter_by(task_id=task_id)
        
        if programming_id:
            query = query.filter_by(programming_id=programming_id)
            
        pt = query.first()

        if not pt:
            return None, "ProgrammingTask not found"
        
        sv_tz = timezone("America/El_Salvador")
        # Use real_end_time from data if available, otherwise now
        val_end = None
        if data and hasattr(data, 'real_end_time') and data.real_end_time:
            val_end = data.real_end_time
        
        if val_end:
            if isinstance(val_end, str):
                pt.real_end_time = datetime.fromisoformat(val_end)
            else:
                pt.real_end_time = val_end
        else:
            pt.real_end_time = datetime.now(sv_tz)
        
        # Use real_quantity from argument if provided, otherwise from data
        final_quantity = real_quantity
        if final_quantity is None and data and hasattr(data, 'real_quantity'):
            final_quantity = data.real_quantity
            
        pt.real_quantity = None if final_quantity is None or (isinstance(final_quantity, str) and final_quantity.strip() == "") else final_quantity

        lote = None
        has_pending_tasks = None
        
        # Si se establece real_end_time, evaluar autocompletado para tareas sin cantidad
        if pt.real_end_time:
            completer_id = current_user.id
            task_has_quantity = False
            
            if pt.task:
                # Verificar si la cantidad es None o cadena vacía
                if pt.task.quantity is None or (isinstance(pt.task.quantity, str) and pt.task.quantity.strip() == ""):
                    task_has_quantity = False
                else:
                    try:
                        # Intentar convertir a float
                        raw_quantity = pt.task.quantity if not isinstance(pt.task.quantity, str) else pt.task.quantity.strip()
                        quantity_value = float(raw_quantity)
                        task_has_quantity = quantity_value > 0
                    except (ValueError, TypeError):
                        task_has_quantity = False

            try:
                # Evaluar condiciones para autocompletar
                should_complete = False
                
                if not task_has_quantity:
                    # Caso 1: Tarea sin cantidad configurada
                    should_complete = True
                elif pt.real_quantity is not None:
                    # Caso 2: Tarea tiene cantidad real reportada
                    try:
                        assigned_qty = None
                        if pt.task and pt.task.quantity is not None:
                            assigned_qty = float(pt.task.quantity)
                        real_qty = float(pt.real_quantity)
                        if assigned_qty is None or assigned_qty == 0:
                            should_complete = True
                        else:
                            should_complete = (real_qty >= assigned_qty)
                    except (ValueError, TypeError):
                        should_complete = False
                else:
                    # Caso 3: Tarea necesita cantidad pero no tiene cantidad real
                    should_complete = False
                    
                # Aplicar la decisión
                if should_complete:
                    pt.is_completed = True
                    pt.completed_by_user_id = completer_id
                    if pt.task:
                        pt.task.is_completed = True
                        lote = pt.task.lote
                else:
                    pt.is_completed = False
                    pt.completed_by_user_id = None
                    
                    try:
                        incomplete_tasks = db.query(ProgrammingTask).filter(
                            ProgrammingTask.programming_id == pt.programming_id,
                            ProgrammingTask.is_completed == False
                        ).count()
                        has_pending_tasks = incomplete_tasks > 0
                    except Exception:
                        has_pending_tasks = True

                db.commit()

            except Exception:
                db.rollback()
                db.refresh(pt)
                return None, "Error during auto-completion processing"

        # Primer commit para guardar los cambios de la tarea actual
        db.commit()
        
        # Actualizar estado de la orden usando el servicio centralizado
        try:
            OrderStatusService.update_order_status_for_task_completion(db, pt)
            db.commit()
        except Exception as e:
            print(f"DEBUG - Error updating order status in stop_timer: {e}")
            db.rollback()

        try:
            db.refresh(pt)
        except Exception:
            pass

        return {
            "pt": pt,
            "lote": lote,
            "has_pending_tasks": has_pending_tasks,
            "is_completed": bool(pt.is_completed)
        }, None

task_timer_service = TaskTimerService()
