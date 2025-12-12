from typing import List
from datetime import datetime
from app.shared.db.session import SessionLocal
from app.shared.utils.core.logging import get_logger
from app.modules.automation.services.task_config import extract_created_orders_data
from app.modules.automation.services.factory import TaskServiceFactory
from app.modules.programming.models import order as order_model

logger = get_logger("services.auto")


def create_tasks_for_lotes(lotes: List[int], username: str):
    db = SessionLocal()
    try:
        logger.info(f"Auto service started for lotes={lotes} by user={username}")
        orders = db.query(order_model.Order).filter(order_model.Order.lote.in_(lotes)).all()
        if not orders:
            logger.warning(f"No orders found for lotes={lotes}")
            return

        # Import OrderFlowService for bin 8 orders
        from app.modules.automation.services.order_flow_service import OrderFlowService

        # Separate orders by type
        bin_8_orders = [o for o in orders if o.bin == 8]
        
        # Only Bin 10 and 100 should have tasks auto-created (besides Bin 8)
        # "Cualquier otro bin -> Cambia de estado a no programable" (implied: no tasks)
        programmable_bins = [10, 100]
        other_orders = [o for o in orders if o.bin in programmable_bins]
        
        # Process Bin 8 orders - pass fabrication orders from same batch for linking
        processed_bin_8 = []
        if bin_8_orders:
            bin_8_result = OrderFlowService.process_bin_8_orders(
                bin_8_orders, 
                db, 
                fabrication_orders_in_batch=other_orders  # órdenes bin 10/100 del mismo archivo
            )
            processed_bin_8 = bin_8_result["processed"]
            # Note: bin_8_result["failed"] contains orders that need manual lot selection
            # These will need to be handled separately in the API layer
        
        orders_to_extract = other_orders + processed_bin_8

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

            # --- Create notification for all programmings that received tasks ---
            try:
                programming_info = []
                
                # Collect programming info from all services
                with open("debug_notification.txt", "w") as f:
                    f.write(f"Start processing. Orders: {len(orders)}\n")
                    
                for service_name, result in [("weighing", weighing_tasks_result), 
                                             ("fabrication", fabrication_tasks_result), 
                                             ("packaging", packaging_tasks_result)]:
                    
                    with open("debug_notification.txt", "a") as f:
                        f.write(f"Service: {service_name}\n")
                        f.write(f"Result keys: {result.keys() if result else 'None'}\n")
                        if result and result.get("created_tasks"):
                            f.write(f"Created tasks count: {len(result['created_tasks'])}\n")
                            f.write(f"Sample task: {str(result['created_tasks'][0])}\n")
                        else:
                            f.write("No created tasks found.\n")

                    if result and result.get("created_tasks"):
                        logger.info(f"Notification processing: Service {service_name} created {len(result['created_tasks'])} tasks")
                        for task_info in result["created_tasks"]:
                            selected_prog = task_info.get("selected_programming")
                            if selected_prog:
                                prog_id = str(selected_prog.get("id"))
                                team_name = selected_prog.get("team_name")
                                prog_date = selected_prog.get("date")
                                
                                # Fallback: Fetch team name from DB if missing
                                if not team_name and prog_id:
                                    try:
                                        from app.modules.programming.models.programming import Programming
                                        from app.modules.core.models.team import Team
                                        
                                        logger.warning(f"Missing team_name for programming {prog_id} in {service_name}. Fetching from DB.")
                                        prog_obj = db.query(Programming).filter(Programming.id == prog_id).first()
                                        if prog_obj:
                                            # Update date if missing
                                            if not prog_date:
                                                prog_date = str(prog_obj.date)
                                                
                                            team_obj = db.query(Team).filter(Team.id == prog_obj.team_id).first()
                                            if team_obj:
                                                team_name = team_obj.name
                                                logger.info(f"Resolved team_name '{team_name}' for programming {prog_id}")
                                    except Exception as e:
                                        logger.error(f"Error resolving team name for {prog_id}: {e}")
                                
                                if prog_id:
                                    programming_info.append({
                                        "programming_id": prog_id,
                                        "team_name": team_name or "Equipo Desconocido",
                                        "programming_date": prog_date,
                                        "service": service_name
                                    })
                    else:
                        logger.info(f"Notification processing: Service {service_name} created 0 tasks or result was empty")
                
                # Aggregate by programming_id to count tasks per programming
                from collections import defaultdict
                prog_map = defaultdict(lambda: {"task_count": 0, "team_name": None, "programming_date": None})
                
                for info in programming_info:
                    prog_id = info["programming_id"]
                    prog_map[prog_id]["task_count"] += 1
                    # Prefer non-null team names
                    if info["team_name"] and info["team_name"] != "Equipo Desconocido":
                        prog_map[prog_id]["team_name"] = info["team_name"]
                    elif not prog_map[prog_id]["team_name"]:
                         prog_map[prog_id]["team_name"] = info["team_name"]
                         
                    if info["programming_date"]:
                        prog_map[prog_id]["programming_date"] = info["programming_date"]
                
                # Convert to list format for storage
                programming_list = [
                    {
                        "programming_id": prog_id,
                        "team_name": data["team_name"] or "Equipo Desconocido",
                        "programming_date": data["programming_date"],
                        "task_count": data["task_count"]
                    }
                    for prog_id, data in prog_map.items()
                ]
                
                # Only create notification if tasks were actually created
                if programming_list:
                    from app.modules.programming.models.task_creation_notification import TaskCreationNotification
                    
                    notification = TaskCreationNotification(
                        created_by=username,
                        programming_info=programming_list,
                        order_count=len(orders)
                    )
                    db.add(notification)
                    db.commit()
                    logger.info(f"Created notification for {len(programming_list)} programmings: {programming_list}")
                else:
                    logger.info("No notification created because programming_list is empty")
                
            except Exception as e:
                logger.error(f"Error creating notification: {e}")
                import traceback
                logger.error(traceback.format_exc())
                # Don't fail the whole process if notification fails
                pass

            logger.info(f"Auto service finished for lotes={lotes}")

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

