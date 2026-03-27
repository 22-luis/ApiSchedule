from typing import List, Optional
from sqlalchemy.orm import Session
from datetime import date
from fastapi import BackgroundTasks, HTTPException

from app.modules.orders.models.order import Order
from app.modules.orders.models.state import OrderStatus
from app.modules.orders.repositories import order_repository, order_rule_repository
from app.modules.warehouse.models.history import WarehouseHistory, WarehouseHistoryType
from app.modules.organization.models.user import User
from app.shared.utils.business.data_cleaning import clean_order_data
from app.modules.automation.services.task_config import extract_created_orders_data, get_orders_summary
from app.modules.automation.services.factory import TaskServiceFactory
from app.modules.automation.repositories.automation_repository import AutomationRepository
from app.modules.automation.services.automation_service import AutomationService
from app.shared.utils.core.logging import get_logger
from app.shared.utils.core.time_utils import TimeZoneUtils

logger = get_logger("order_service")

class OrderService:
    @staticmethod
    def create_orders(db: Session, orders_data: List[any], auto_create_tasks: bool, current_user: User, background_tasks: BackgroundTasks = None):
        created_orders = []
        for order in orders_data:
            if order_repository.find_by_lote(db, order.lote):
                logger.info(f"Order with lote {order.lote} already exists. SKIPPING.")
                continue 
            
            order_dict = order.dict() if hasattr(order, 'dict') else order.model_dump()
            cleaned_order = clean_order_data(order_dict)
            order_code = cleaned_order['code']
            initial_status = OrderStatus.unprogrammed

            # Aplicar excepciones de código (OrderRule)
            special_rule = order_rule_repository.find_by_code(db, order_code)
            if special_rule:
                if special_rule.programming_code:
                    logger.info(f"Applying OrderRule rule: {order_code} -> {special_rule.programming_code}")
                    order_code = special_rule.programming_code
                else:
                    logger.info(f"Applying OrderRule rule: {order_code} is NOT PROGRAMMABLE")
                    initial_status = OrderStatus.not_programmable

            # Si no es un bin programable y no fue forzado por OrderRule, marcar como no programable
            if initial_status != OrderStatus.not_programmable and order.bin not in [8, 10, 100]:
                initial_status = OrderStatus.not_programmable
            
            db_order = Order(
                lote=order.lote,
                dueDate=order.dueDate,
                code=order_code,
                description=cleaned_order['description'],
                quantity=order.quantity,
                missing_quantity=order.quantity,
                bin=order.bin,
                status=initial_status
            )
            db.add(db_order)
            created_orders.append(db_order)

        db.commit()
        for db_order in created_orders:
            db.refresh(db_order)
        
        extracted_orders = extract_created_orders_data(created_orders)
        summary = get_orders_summary(created_orders)
        
        serialized_orders = [
            {
                "lote": int(o.lote),
                "code": o.code,
                "status": o.status.name if hasattr(o.status, 'name') else str(o.status),
                "description": o.description,
                "quantity": float(o.quantity) if o.quantity is not None else 0.0,
                "bin": int(o.bin) if o.bin is not None else None,
                "dueDate": o.dueDate.isoformat() if hasattr(o.dueDate, 'isoformat') else o.dueDate
            } for o in created_orders
        ]
        
        response_data = {
            "created_orders": serialized_orders,
            "extracted_orders": extracted_orders,
            "summary": summary,
            "auto_create_tasks": auto_create_tasks
        }
        
        bin8_orders = [o for o in created_orders if o.bin == 8]
        other_orders = [o for o in created_orders if o.bin != 8]
        bin8_failed = []
        
        if bin8_orders:
            from app.modules.automation.services.order_flow_service import OrderFlowService
            bin_8_result = OrderFlowService.process_bin_8_orders(
                bin8_orders, db, fabrication_orders_in_batch=[o for o in created_orders if o.bin in [10, 100]]
            )
            
            processed_bin8 = bin_8_result["processed"]
            failed_bin8_raw = bin_8_result["failed"]
            other_orders.extend(bin_8_result.get("self_sufficient", []))
            
            if processed_bin8:
                extracted_orders_bin8 = extract_created_orders_data(processed_bin8)
                for i, extracted in enumerate(extracted_orders_bin8):
                    original_order = processed_bin8[i]
                    if hasattr(original_order, '_usar_lote_fabricacion'):
                        extracted['lote'] = original_order._usar_lote_fabricacion
                        extracted['original_packaging_lote'] = original_order._original_packaging_lote
                        extracted['bin'] = original_order.bin

                packaging_service = TaskServiceFactory.create_packaging_service()
                try:
                    packaging_result = packaging_service.create_packaging_tasks_for_orders(extracted_orders_bin8, db)
                    if packaging_result and packaging_result.get("tasks_created", 0) > 0:
                        db.commit()
                        OrderService._create_notification(db, current_user.username, packaging_result.get("created_tasks", []), len(processed_bin8))
                except Exception as e:
                    logger.error(f"Error creating tasks synchronously: {e}")
            
            for failed_info in failed_bin8_raw:
                order = failed_info["order"]
                bin8_failed.append({
                    "lote": int(order.lote),
                    "code": order.code,
                    "description": order.description,
                    "quantity": float(order.quantity),
                    "bin": int(order.bin),
                    "dueDate": order.dueDate.isoformat() if hasattr(order.dueDate, 'isoformat') else order.dueDate,
                    "fabrication_code": failed_info.get("fabrication_code"),
                    "reason": failed_info["reason"]
                })
        
        if auto_create_tasks and other_orders:
            other_lotes = [o.lote for o in other_orders]
            automation_service = AutomationService(AutomationRepository(db))
            if background_tasks is not None:
                background_tasks.add_task(automation_service.create_tasks_for_lotes, other_lotes, current_user.username)
                response_data.update({"task_creation_scheduled": True})
            else:
                automation_service.create_tasks_for_lotes(other_lotes, current_user.username)
                response_data.update({"task_creation_scheduled": False})
        
        if bin8_failed:
            response_data["bin8_failed"] = bin8_failed
            
        return response_data

    @staticmethod
    def get_paged_orders(db: Session, filters: dict):
        skip = filters.pop("skip", 0)
        limit = filters.pop("limit", 10)
        
        total = order_repository.count_all(db, **filters)
        orders = order_repository.find_all(db, skip=skip, limit=limit, **filters)
        
        serialized_orders = []
        for order in orders:
            serialized_orders.append({
                "lote": order.lote,
                "code": order.code,
                "status": order.status,
                "description": order.description,
                "quantity": order.quantity,
                "bin": order.bin,
                "dueDate": order.dueDate,
                "received_user": order.received_user,
                "received_date": order.received_date,
                "received_quantity": order.received_quantity,
                "missing_quantity": order.missing_quantity,
                "submitted_user": order.submitted_user,
                "submitted_date": order.submitted_date,
                "submitted_observations": order.submitted_observations,
                "is_hidden": order.is_hidden
            })
        return {"orders": serialized_orders, "total": total}

    @staticmethod
    def receive_order(db: Session, order_id: str, custom_status: Optional[str], current_user: User):
        db_order = order_repository.find_by_lote(db, order_id)
        if not db_order:
            raise HTTPException(status_code=404, detail="Order not found")
        
        if db_order.status not in [OrderStatus.delivered, OrderStatus.not_programmable]:
            raise HTTPException(status_code=400, detail="La orden debe estar en estado 'entregado' o 'no programable' para poder ser recibida")

        if db_order.status == OrderStatus.completed:
            raise HTTPException(status_code=400, detail="La orden ya está completada")
        
        db_order.received_user = current_user.username
        db_order.received_date = date.today()

        if custom_status:
            db_order.status = OrderStatus.pending if custom_status == "pending" else OrderStatus.completed
            status_message = "Pendiente" if custom_status == "pending" else "Completada"
        else:
            current_missing = db_order.missing_quantity if db_order.missing_quantity is not None else 0
            if current_missing > 0:
                db_order.status = OrderStatus.pending
                status_message = "pendiente (quedan faltantes)"
            else:
                db_order.status = OrderStatus.completed
                status_message = "completada"

        history = WarehouseHistory(
            lote=db_order.lote,
            code=db_order.code,
            quantity=db_order.received_quantity if db_order.received_quantity is not None else 0,
            type=WarehouseHistoryType.RECEIVED,
            user=current_user.username,
            observations=f"Orden recibida. Estado: {status_message}"
        )
        db.add(history)
        db.commit()
        db.refresh(db_order)
        
        return {
            "message": f"Orden {order_id} recibida exitosamente - Estado: {status_message}",
            "lote": db_order.lote,
            "status": db_order.status,
            "received_user": db_order.received_user,
            "received_date": db_order.received_date,
            "received_quantity": db_order.received_quantity,
            "missing_quantity": db_order.missing_quantity,
            "status_message": status_message
        }

    @staticmethod
    def deliver_order(db: Session, order_id: int, delivered_quantity: float, observations: Optional[str], current_user: User):
        db_order = order_repository.find_by_lote(db, order_id)
        if not db_order:
            raise HTTPException(status_code=404, detail="Order not found")

        db_order.submitted_user = current_user.username
        db_order.submitted_date = date.today()
        db_order.submitted_observations = observations
        
        current_received = db_order.received_quantity if db_order.received_quantity is not None else 0
        new_received_total = current_received + delivered_quantity
        db_order.received_quantity = new_received_total
        
        if db_order.quantity is not None:
            new_missing_quantity = db_order.quantity - new_received_total
            db_order.missing_quantity = new_missing_quantity
        else:
            new_missing_quantity = -new_received_total
            db_order.missing_quantity = new_missing_quantity

        db_order.status = OrderStatus.delivered
        
        history = WarehouseHistory(
            lote=db_order.lote,
            code=db_order.code,
            quantity=delivered_quantity,
            type=WarehouseHistoryType.SENT,
            user=current_user.username,
            observations=observations
        )
        db.add(history)
        db.commit()
        db.refresh(db_order)
        
        return {
            "lote": db_order.lote,
            "code": db_order.code,
            "status": db_order.status,
            "received_quantity": db_order.received_quantity,
            "missing_quantity": db_order.missing_quantity,
            "delivered_quantity": delivered_quantity,
            "submitted_user": db_order.submitted_user,
            "submitted_date": db_order.submitted_date,
            "message": f"Entrega realizada exitosamente. Cantidad faltante: {db_order.missing_quantity}"
        }


    @staticmethod
    def delete_order(db: Session, order_id: str):
        db_order = order_repository.find_by_lote(db, order_id)
        if not db_order:
            raise HTTPException(status_code=404, detail="Order not found")
        order_repository.delete(db, db_order)
        return {"message": "Order deleted successfully. Tasks were preserved."}

    @staticmethod
    def update_order_status(db: Session, order_id: str, status: str):
        db_order = order_repository.find_by_lote(db, order_id)
        if not db_order:
            raise HTTPException(status_code=404, detail="Order not found")
        
        db_order.status = status
        db.commit()
        db.refresh(db_order)
        return {
            "lote": db_order.lote, "code": db_order.code, "status": db_order.status,
            "description": db_order.description, "quantity": db_order.quantity,
            "bin": db_order.bin, "dueDate": db_order.dueDate, "missing_quantity": db_order.missing_quantity
        }

    @staticmethod
    def hide_order(db: Session, order_id: int, is_hidden: bool):
        db_order = order_repository.find_by_lote(db, order_id)
        if not db_order:
            raise HTTPException(status_code=404, detail="Order not found")
        db_order.is_hidden = is_hidden
        db_order.hidden_at = TimeZoneUtils.get_now() if is_hidden else None
        db.commit()
        return {"message": "Visibilidad de la orden actualizada", "is_hidden": db_order.is_hidden}

    @staticmethod
    def sync_order_statuses(db: Session, order_ids: Optional[List[int]] = None):
        from app.shared.utils.business.order_status_service import OrderStatusService
        
        query = db.query(Order)
        if order_ids:
            query = query.filter(Order.lote.in_(order_ids))
        orders = query.all()
        
        synced_count = 0
        for order in orders:
            try:
                OrderStatusService.sync_order_status_for_lote(db, str(order.lote))
                synced_count += 1
            except Exception:
                continue
        return {"message": f"Synced {synced_count} out of {len(orders)} orders"}


    @staticmethod
    def _create_notification(db, username, created_tasks_info, order_count):
        try:
            from collections import defaultdict
            from app.modules.programming.models.task_creation_notification import TaskCreationNotification
            
            prog_map = defaultdict(lambda: {"task_count": 0, "team_name": None, "programming_date": None})
            for task_info in created_tasks_info:
                selected_prog = task_info.get("selected_programming")
                if selected_prog:
                    prog_id = str(selected_prog.get("id"))
                    prog_map[prog_id]["task_count"] += 1
                    prog_map[prog_id]["team_name"] = selected_prog.get("team_name")
                    prog_date = selected_prog.get("date")
                    prog_map[prog_id]["programming_date"] = str(prog_date.strftime('%Y-%m-%d') if hasattr(prog_date, 'strftime') else prog_date)
            
            programming_info_list = [
                {"programming_id": prog_id, "team_name": d["team_name"], "programming_date": d["programming_date"], "task_count": d["task_count"]}
                for prog_id, d in prog_map.items()
            ]
            
            if programming_info_list:
                notification = TaskCreationNotification(created_by=username, programming_info=programming_info_list, order_count=order_count)
                db.add(notification)
                db.commit()
        except Exception as e:
            logger.error(f"Error creating notification: {e}")
