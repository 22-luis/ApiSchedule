from typing import List, Dict, Any
from datetime import datetime
from app.shared.utils.core.logging import get_logger
from app.shared.utils.core.time_utils import TimeZoneUtils
from app.modules.automation.services.task_config import extract_created_orders_data
from app.modules.automation.services.factory import TaskServiceFactory
from app.modules.automation.repositories.automation_repository import AutomationRepository

logger = get_logger("services.automation")

class AutomationService:
    def __init__(self, automation_repo: AutomationRepository):
        self.automation_repo = automation_repo

    def create_tasks_for_lotes(self, lotes: List[int], username: str) -> Dict[str, Any]:
        """
        Creates tasks for a list of lotes.
        Moved from auto.py to service class for standardization.
        """
        db = self.automation_repo.db
        try:
            logger.info(f"Automation service started for lotes={lotes} by user={username}")
            orders = self.automation_repo.get_orders_by_lotes(lotes)
            if not orders:
                logger.warning(f"No orders found for lotes={lotes}")
                return {"error": "No orders found"}

            # Populate _programming_code for downstream extraction
            from app.modules.orders.repositories import order_rule_repository
            for o in orders:
                rule = order_rule_repository.find_by_code(db, o.code)
                if rule and rule.programming_code:
                    o._programming_code = rule.programming_code
                else:
                    o._programming_code = o.code

            # Import OrderFlowService for bin 8 orders
            from app.modules.automation.services.order_flow_service import OrderFlowService

            # Separate orders by type
            bin_8_orders = [o for o in orders if o.bin == 8]
            
            # Only Bin 10 and 100 should have tasks auto-created (besides Bin 8)
            programmable_bins = [10, 100]
            other_orders = [o for o in orders if o.bin in programmable_bins]
            
            # Process Bin 8 orders
            processed_bin_8 = []
            if bin_8_orders:
                bin_8_result = OrderFlowService.process_bin_8_orders(
                    bin_8_orders, 
                    db, 
                    fabrication_orders_in_batch=other_orders
                )
                processed_bin_8 = bin_8_result["processed"]
                self_sufficient_bin_8 = bin_8_result.get("self_sufficient", [])
            else:
                self_sufficient_bin_8 = []
            
            orders_to_extract = other_orders + processed_bin_8 + self_sufficient_bin_8

            # Prepare extracted orders used by services
            extracted_orders = extract_created_orders_data(orders_to_extract)
            
            # For bin 8 orders, replace the lote with the fabrication order's lote
            for i, extracted in enumerate(extracted_orders):
                original_order = orders_to_extract[i]
                if hasattr(original_order, '_usar_lote_fabricacion'):
                    extracted['lote'] = original_order._usar_lote_fabricacion
                    extracted['original_packaging_lote'] = original_order._original_packaging_lote
                    extracted['bin'] = original_order.bin

            # Get worker services from factory
            weighing_service = TaskServiceFactory.create_weighing_service()
            fabrication_service = TaskServiceFactory.create_fabrication_service()
            packaging_service = TaskServiceFactory.create_packaging_service()

            summary: Dict[str, Any] = {}

            # 1. Weighing
            weighing_activities = weighing_service.get_weighing_activities_with_minutes(extracted_orders, db)
            weighing_codes = set(weighing_activities.get("weighing_activities_with_minutes", {}).get("weighing_activities_with_minutes_by_code", {}).keys())
            weighing_orders = [o for o in extracted_orders if o.get("code") in weighing_codes]
            
            weighing_tasks_result = None
            if weighing_orders:
                weighing_tasks_result = weighing_service.create_weighing_tasks_for_orders(weighing_orders, db)
                if weighing_tasks_result and weighing_tasks_result.get("tasks_created", 0) > 0:
                    db.commit()
            summary["weighing"] = weighing_tasks_result or {"tasks_created": 0}

            # 2. Fabrication
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

            # 3. Packaging
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

            # 4. Notifications
            self._create_notification(username, orders, weighing_tasks_result, fabrication_tasks_result, packaging_tasks_result)

            logger.info(f"Automation service finished for lotes={lotes}")
            return {
                "lotes": lotes,
                "created_orders_count": len(orders),
                "summary": summary,
                "timestamp": TimeZoneUtils.get_now().isoformat()
            }
        except Exception as e:
            logger.exception(f"Error in automation for lotes={lotes}: {e}")
            db.rollback()
            raise

    def _create_notification(self, username, orders, weighing_res, fab_res, pack_res):
        """Helper to create notification after task creation"""
        from collections import defaultdict
        db = self.automation_repo.db
        
        programming_info = []
        for service_name, result in [("weighing", weighing_res), ("fabrication", fab_res), ("packaging", pack_res)]:
            if result and result.get("tasks_created", 0) > 0 and result.get("created_tasks"):
                for task_info in result["created_tasks"]:
                    selected_prog = task_info.get("selected_programming")
                    if selected_prog:
                        prog_id = selected_prog.get("id")
                        if prog_id and str(prog_id).lower() != "none":
                            # Resolve team name and date
                            team_name = selected_prog.get("team_name")
                            prog_date = selected_prog.get("date")
                            
                            if not team_name:
                                prog_obj = self.automation_repo.get_programming_by_id(str(prog_id))
                                if prog_obj:
                                    prog_date = str(prog_obj.date)
                                    team_obj = self.automation_repo.get_team_by_id(prog_obj.team_id)
                                    if team_obj:
                                        team_name = team_obj.name

                            programming_info.append({
                                "programming_id": str(prog_id),
                                "team_name": team_name or "Equipo Desconocido",
                                "programming_date": prog_date,
                            })

        if programming_info:
            prog_map: Dict[str, Dict[str, Any]] = defaultdict(lambda: {"task_count": 0, "team_name": None, "programming_date": None})
            for info in programming_info:
                prog_id = info["programming_id"]
                prog_map[prog_id]["task_count"] = (prog_map[prog_id].get("task_count") or 0) + 1
                if info["team_name"] and info["team_name"] != "Equipo Desconocido":
                    prog_map[prog_id]["team_name"] = info["team_name"]
                elif not prog_map[prog_id]["team_name"]:
                    prog_map[prog_id]["team_name"] = info["team_name"]
                if info["programming_date"]:
                    prog_map[prog_id]["programming_date"] = info["programming_date"]
            
            programming_list = [
                {
                    "programming_id": pid,
                    "team_name": d["team_name"] or "Equipo Desconocido",
                    "programming_date": d["programming_date"],
                    "task_count": d["task_count"]
                }
                for pid, d in prog_map.items()
            ]

            from app.modules.programming.models.task_creation_notification import TaskCreationNotification
            notification = TaskCreationNotification(
                created_by=username,
                programming_info=programming_list,
                order_count=len(orders)
            )
            self.automation_repo.save_notification(notification)
