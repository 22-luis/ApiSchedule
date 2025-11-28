from typing import List
from datetime import datetime
from app.shared.db.session import SessionLocal
from app.shared.utils.core.logging import get_logger
from app.modules.programming.services.task_config import extract_created_orders_data
from app.modules.programming.services.factory import TaskServiceFactory
from app.modules.programming.models import order as order_model

logger = get_logger("services.auto")


def create_tasks_for_lotes(lotes: List[int], username: str):
    """
    Worker that creates weighing, fabrication and packaging tasks for the given lotes.
    Creates its own DB session so it is safe to run as a background task.
    """
    db = SessionLocal()
    try:
        logger.info(f"Auto service started for lotes={lotes} by user={username}")
        orders = db.query(order_model.Order).filter(order_model.Order.lote.in_(lotes)).all()
        if not orders:
            logger.warning(f"No orders found for lotes={lotes}")
            return

        # Import fabrication code finder for bin 8 orders
        from app.shared.utils.business.fabrication_code_finder import FabricationCodeFinder
        from app.modules.programming.models.state import OrderStatus

        # Prepare extracted orders with special handling for bin 8
        orders_to_extract = []
        for order in orders:
            # For bin 8 (packaging orders), find fabrication code and manufactured order
            if order.bin == 8:
                logger.info(f"Processing bin 8 order {order.lote} with code: {order.code}")
                
                # Find manufactured order using fabrication code finder
                fab_order_info = FabricationCodeFinder.find_manufactured_order(
                    packaging_code=order.code,
                    packaging_quantity=order.quantity,
                    db=db
                )
                
                if not fab_order_info:
                    logger.warning(
                        f"No manufactured order found for packaging order {order.lote}. "
                        f"Code: {order.code}, Quantity: {order.quantity}. "
                        f"Skipping task creation for this order."
                    )
                    continue
                
                logger.info(
                    f"Found manufactured order {fab_order_info['lote']} for packaging order {order.lote}. "
                    f"Fabrication code: {fab_order_info['code']}, Quantity: {order.quantity}"
                )
                
                # Use the fabrication order's lote for task creation
                # but keep track of the original packaging order
                order._original_packaging_lote = order.lote
                order._usar_lote_fabricacion = fab_order_info['lote']
                
                # Update packaging order status to programmed
                order.status = OrderStatus.programmed
                db.commit()
                logger.info(f"Updated packaging order {order.lote} status to 'programmed'")
                
                orders_to_extract.append(order)
            else:
                # For non-bin-8 orders, process normally
                orders_to_extract.append(order)

        # Prepare extracted orders used by services (list of dicts with lote, code, quantity)
        extracted_orders = extract_created_orders_data(orders_to_extract)
        
        # For bin 8 orders, replace the lote with the fabrication order's lote
        for i, extracted in enumerate(extracted_orders):
            original_order = orders_to_extract[i]
            if hasattr(original_order, '_usar_lote_fabricacion'):
                logger.info(
                    f"Using fabrication lote {original_order._usar_lote_fabricacion} "
                    f"instead of packaging lote {extracted['lote']} for task creation"
                )
                extracted['lote'] = original_order._usar_lote_fabricacion
                extracted['original_packaging_lote'] = original_order._original_packaging_lote
                extracted['bin'] = original_order.bin

        weighing_service = TaskServiceFactory.create_weighing_service()
        fabrication_service = TaskServiceFactory.create_fabrication_service()
        packaging_service = TaskServiceFactory.create_packaging_service()

        # We'll run each service only for the orders that actually have activities for that service.
        try:
            summary = {
                "weighing": None,
                "fabrication": None,
                "packaging": None
            }

            # --- Weighing: find which codes have weighing activities and process only those ---
            weighing_activities = weighing_service.get_weighing_activities_with_minutes(extracted_orders, db)
            weighing_codes = set(weighing_activities.get("weighing_activities_with_minutes", {}).get("weighing_activities_with_minutes_by_code", {}).keys())
            weighing_orders = [o for o in extracted_orders if o.get("code") in weighing_codes]
            logger.info(f"Weighing: Found {len(weighing_codes)} codes with weighing activities: {weighing_codes}")
            logger.info(f"Weighing: Processing {len(weighing_orders)} orders")

            weighing_tasks_result = None
            if weighing_orders:
                weighing_tasks_result = weighing_service.create_weighing_tasks_for_orders(weighing_orders, db)
                logger.info(f"Weighing: Result = {weighing_tasks_result}")
                if weighing_tasks_result and weighing_tasks_result.get("tasks_created", 0) > 0:
                    db.commit()
            else:
                logger.warning(f"Weighing: No orders to process (weighing_codes={weighing_codes})")
            summary["weighing"] = weighing_tasks_result or {"tasks_created": 0}

            # --- Fabrication: process only orders that have fabrication activities ---
            fabrication_activities = fabrication_service.get_fabrication_activities_with_minutes(extracted_orders, db)
            fabrication_codes = set(fabrication_activities.get("fabrication_activities_with_minutes", {}).get("fabrication_activities_with_minutes_by_code", {}).keys())
            fabrication_orders = [o for o in extracted_orders if o.get("code") in fabrication_codes]
            logger.info(f"Fabrication: Found {len(fabrication_codes)} codes with fabrication activities: {fabrication_codes}")
            logger.info(f"Fabrication: Processing {len(fabrication_orders)} orders")

            fabrication_tasks_result = None
            if fabrication_orders:
                fabrication_tasks_result = fabrication_service.create_fabrication_tasks_for_orders(
                    fabrication_orders, db, weighing_results=weighing_tasks_result
                )
                logger.info(f"Fabrication: Result = {fabrication_tasks_result}")
                if fabrication_tasks_result and fabrication_tasks_result.get("tasks_created", 0) > 0:
                    db.commit()
            else:
                logger.warning(f"Fabrication: No orders to process (fabrication_codes={fabrication_codes})")
            summary["fabrication"] = fabrication_tasks_result or {"tasks_created": 0}

            # --- Packaging: process only orders that have packaging activities ---
            packaging_activities = packaging_service.get_packaging_activities_with_minutes(extracted_orders, db)
            packaging_codes = set(packaging_activities.get("packaging_activities_with_minutes", {}).get("packaging_activities_with_minutes_by_code", {}).keys())
            packaging_orders = [o for o in extracted_orders if o.get("code") in packaging_codes]
            logger.info(f"Packaging: Found {len(packaging_codes)} codes with packaging activities: {packaging_codes}")
            logger.info(f"Packaging: Processing {len(packaging_orders)} orders")

            packaging_tasks_result = None
            if packaging_orders:
                packaging_tasks_result = packaging_service.create_packaging_tasks_for_orders(
                    packaging_orders, db, fabrication_results=fabrication_tasks_result
                )
                logger.info(f"Packaging: Result = {packaging_tasks_result}")
                if packaging_tasks_result and packaging_tasks_result.get("tasks_created", 0) > 0:
                    db.commit()
            else:
                logger.warning(f"Packaging: No orders to process (packaging_codes={packaging_codes})")
            summary["packaging"] = packaging_tasks_result or {"tasks_created": 0}

            logger.info(f"Auto service finished for lotes={lotes}")

            # Return a consolidated summary (useful when running inline)
            return {
                "lotes": lotes,
                "created_orders_count": len(orders),
                "summary": summary,
                "timestamp": datetime.utcnow().isoformat()
            }
        except Exception as e:
            logger.exception(f"Error in auto task creation for lotes={lotes}: {e}")
            try:
                db.rollback()
            except Exception:
                pass
    finally:
        db.close()
