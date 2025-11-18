from typing import List
import datetime
from app.db.session import SessionLocal
from app.utils.core.logging import get_logger
from app.core.task_config import extract_created_orders_data
from app.services.factory import TaskServiceFactory
from app.models import order as order_model

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

        # Prepare extracted orders used by services (list of dicts with lote, code, quantity)
        extracted_orders = extract_created_orders_data(orders)

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

            weighing_tasks_result = None
            if weighing_orders:
                weighing_tasks_result = weighing_service.create_weighing_tasks_for_orders(weighing_orders, db)
                if weighing_tasks_result and weighing_tasks_result.get("tasks_created", 0) > 0:
                    db.commit()
            summary["weighing"] = weighing_tasks_result or {"tasks_created": 0}

            # --- Fabrication: process only orders that have fabrication activities ---
            fabrication_activities = fabrication_service.get_fabrication_activities_with_minutes(extracted_orders, db)
            fabrication_codes = set(fabrication_activities.get("fabrication_activities_with_minutes", {}).get("fabrication_activities_with_minutes_by_code", {}).keys())
            fabrication_orders = [o for o in extracted_orders if o.get("code") in fabrication_codes]

            fabrication_tasks_result = None
            if fabrication_orders:
                fabrication_tasks_result = fabrication_service.create_fabrication_tasks_for_orders(
                    fabrication_orders, db, weighing_results=weighing_tasks_result
                )
                if fabrication_tasks_result and fabrication_tasks_result.get("tasks_created", 0) > 0:
                    db.commit()
            summary["fabrication"] = fabrication_tasks_result or {"tasks_created": 0}

            # --- Packaging: process only orders that have packaging activities ---
            packaging_activities = packaging_service.get_packaging_activities_with_minutes(extracted_orders, db)
            packaging_codes = set(packaging_activities.get("packaging_activities_with_minutes", {}).get("packaging_activities_with_minutes_by_code", {}).keys())
            packaging_orders = [o for o in extracted_orders if o.get("code") in packaging_codes]

            packaging_tasks_result = None
            if packaging_orders:
                packaging_tasks_result = packaging_service.create_packaging_tasks_for_orders(
                    packaging_orders, db, fabrication_results=fabrication_tasks_result
                )
                if packaging_tasks_result and packaging_tasks_result.get("tasks_created", 0) > 0:
                    db.commit()
            summary["packaging"] = packaging_tasks_result or {"tasks_created": 0}

            logger.info(f"Auto service finished for lotes={lotes}")

            # Return a consolidated summary (useful when running inline)
            return {
                "lotes": lotes,
                "created_orders_count": len(orders),
                "summary": summary,
                "timestamp": datetime.datetime.utcnow().isoformat()
            }
        except Exception as e:
            logger.exception(f"Error in auto task creation for lotes={lotes}: {e}")
            try:
                db.rollback()
            except Exception:
                pass
    finally:
        db.close()
