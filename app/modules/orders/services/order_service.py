import traceback
from typing import List, Union, Optional
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_
from fastapi import BackgroundTasks
from app.modules.orders.schemas.order import OrderCreate
from app.modules.warehouse.models.history import WarehouseHistory, WarehouseHistoryType
from app.modules.orders.models import order as order_model
from app.modules.organization.models.user import User
from app.modules.organization.models.role import UserRole
from app.modules.orders.models.state import OrderStatus
from app.shared.utils.business.data_cleaning import clean_order_data
from app.modules.automation.services.task_config import extract_created_orders_data, get_orders_summary
from app.modules.automation.services.factory import TaskServiceFactory
from app.modules.automation.services.auto import create_tasks_for_lotes
from app.shared.utils.business.order_status_service import OrderStatusService
from app.modules.programming.models.programming import ProgrammingTask
from app.shared.utils.core.logging import get_logger

logger = get_logger("order_service")

class OrderService:
    @staticmethod
    def create_orders(db: Session, orders_data: List[OrderCreate], auto_create_tasks: bool, current_user: User, background_tasks: BackgroundTasks = None):
        """
        Creates new orders and optionally triggers automatic task creation.
        Handles complex logic for Bin 8 orders synchronously.
        """
        logger.info(f"Received request to create orders. auto_create_tasks={auto_create_tasks}")
        
        created_orders = []
        for order in orders_data:
            # Verificar si la orden ya existe por el lote
            existing_order = db.query(order_model.Order).filter(order_model.Order.lote == order.lote).first()
            if existing_order:
                logger.info(f"Order with lote {order.lote} already exists. SKIPPING.")
                continue 
            
            # Limpiar los datos de la orden
            order_dict = order.dict()
            cleaned_order = clean_order_data(order_dict)
            
            initial_status = OrderStatus.unprogrammed
            # Not programmable condition
            if order.bin not in [8, 10, 100]:
                initial_status = OrderStatus.not_programmable
            
            db_order = order_model.Order(
                lote=order.lote,
                dueDate=order.dueDate,
                code=cleaned_order['code'],
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
        
        # Extracted data for task creation services
        extracted_orders = extract_created_orders_data(created_orders)
        summary = get_orders_summary(created_orders)
        
        # Serialize orders for response
        serialized_orders = []
        for order in created_orders:
            status_val = order.status.name if hasattr(order.status, 'name') else str(order.status)
            due_date_val = order.dueDate.isoformat() if hasattr(order.dueDate, 'isoformat') else order.dueDate
            serialized_orders.append({
                "lote": int(order.lote) if order.lote is not None else None,
                "code": order.code,
                "status": status_val,
                "description": order.description,
                "quantity": float(order.quantity) if order.quantity is not None else 0.0,
                "bin": int(order.bin) if order.bin is not None else None,
                "dueDate": due_date_val
            })
        
        response_data = {
            "created_orders": serialized_orders,
            "extracted_orders": extracted_orders,
            "summary": summary,
            "auto_create_tasks": auto_create_tasks
        }
        
        # Separate Bin 8 orders
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
            self_sufficient_bin8 = bin_8_result.get("self_sufficient", [])
            other_orders.extend(self_sufficient_bin8)
            
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
            
            # Prepare failed info for response
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
        
        # Trigger task creation for non-Bin 8 (and self-sufficient) orders
        if auto_create_tasks and other_orders:
            other_lotes = [o.lote for o in other_orders]
            if background_tasks is not None:
                background_tasks.add_task(create_tasks_for_lotes, other_lotes, current_user.username)
                response_data.update({"task_creation_scheduled": True})
            else:
                create_tasks_for_lotes(other_lotes, current_user.username)
                response_data.update({"task_creation_scheduled": False})
        
        if bin8_failed:
            response_data["bin8_failed"] = bin8_failed
            
        return response_data

    @staticmethod
    def create_tasks_for_bin8_manual(db: Session, order_lote: int, fabrication_lote: int, current_user: User):
        """
        Manually create tasks for a bin 8 order with a specified fabrication lot.
        """
        logger.info(f"Manual task creation requested for order {order_lote} with fabrication lot {fabrication_lote}")
        
        # Obtener la orden de empaque
        packaging_order = db.query(order_model.Order).filter(
            order_model.Order.lote == order_lote
        ).first()
        
        if not packaging_order:
            return None, f"Order {order_lote} not found"
        
        if packaging_order.bin != 8:
            return None, f"Order {order_lote} is not a bin 8 (packaging) order"
        
        # Verificar que el lote de fabricación existe
        fabrication_order = db.query(order_model.Order).filter(
            order_model.Order.lote == fabrication_lote
        ).first()
        
        if not fabrication_order:
            return None, f"Fabrication lot {fabrication_lote} not found"
        
        # Cambiar estado de la orden
        packaging_order.status = OrderStatus.programmed
        db.commit()
        
        # Extract order data but replace lote with fabrication lote
        extracted = {
            "lote": fabrication_lote,
            "code": packaging_order.code,
            "quantity": packaging_order.quantity,
            "bin": packaging_order.bin,
            "original_packaging_lote": order_lote
        }
        
        # Get packaging service and create tasks
        packaging_service = TaskServiceFactory.create_packaging_service()
        
        try:
            result = packaging_service.create_packaging_tasks_for_orders([extracted], db)
            if result and result.get("tasks_created", 0) > 0:
                db.commit()
                OrderService._create_notification(db, current_user.username, result.get("created_tasks", []), 1)
                return result, None
            else:
                return None, "No se crearon tareas. Verifica los logs del servidor."
        except Exception as e:
            db.rollback()
            return None, str(e)

    @staticmethod
    def _create_notification(db, username, created_tasks_info, order_count):
        """Helper to create TaskCreationNotification."""
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
