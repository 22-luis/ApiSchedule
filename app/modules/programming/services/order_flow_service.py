from typing import List, Dict, Optional
from sqlalchemy.orm import Session
from app.modules.programming.models import order as order_model
from app.modules.programming.models.state import OrderStatus
from app.shared.utils.business.fabrication_code_finder import FabricationCodeFinder
from app.shared.utils.core.logging import get_logger

logger = get_logger("services.order_flow")

class OrderFlowService:
    """
    Service to handle specific order flow logic based on Bin type.
    """

    @staticmethod
    def process_bin_8_orders(orders: List[order_model.Order], db: Session) -> List[order_model.Order]:
        """
        Process Bin 8 (Packaging) orders:
        1. Find associated manufactured order.
        2. Consume 'fabricated_quantity'.
        3. Update manufactured order status if exhausted.
        4. Prepare order object for task creation (swap lote).
        """
        processed_orders = []
        
        for order in orders:
            if order.bin != 8:
                continue

            logger.info(f"Processing Bin 8 order {order.lote} ({order.code})...")
            
            # 1. Find fabrication code
            fabrication_code = FabricationCodeFinder.find_fabrication_code(order.code, db)
            
            if not fabrication_code:
                logger.warning(f"Could not find fabrication code for order {order.lote} ({order.code}). Skipping.")
                continue

            # 2. Find available manufactured order (fabricated_quantity >= order.quantity)
            # IMPORTANTE: Excluir órdenes que ya están empacadas (packaged)
            # Buscamos una orden que tenga SUFICIENTE cantidad para cubrir el requerimiento
            manufactured_order = db.query(order_model.Order).filter(
                order_model.Order.code == fabrication_code,
                order_model.Order.status == OrderStatus.manufactured,
                order_model.Order.fabricated_quantity >= order.quantity
            ).order_by(order_model.Order.lote.asc()).first()

            if not manufactured_order:
                logger.warning(f"No available manufactured order with sufficient quantity found for {order.code} (Req: {order.quantity}). Skipping.")
                continue

            logger.info(f"Found manufactured order {manufactured_order.lote} with {manufactured_order.fabricated_quantity} available.")

            # 3. Consume quantity
            quantity_to_consume = order.quantity
            current_available = manufactured_order.fabricated_quantity
            
            new_available = current_available - quantity_to_consume
            manufactured_order.fabricated_quantity = max(0.0, new_available)
            
            # 4. Update status if exhausted
            if manufactured_order.fabricated_quantity <= 0:
                manufactured_order.status = OrderStatus.packaged
                logger.info(f"Manufactured order {manufactured_order.lote} exhausted. Status changed to 'packaged'.")
            
            db.add(manufactured_order)
            db.flush() # CRITICAL: Flush changes so next iteration sees updated quantity
            
            # 5. Prepare for task creation
            # "A la hora de crear la tarea de empaque debe usar el lote de fabricado"
            # We attach metadata to the order object so auto.py knows what to do
            order._usar_lote_fabricacion = manufactured_order.lote
            order._original_packaging_lote = order.lote
            
            # Update the packaging order status to programmed as it is being processed
            order.status = OrderStatus.programmed
            db.add(order)
            
            processed_orders.append(order)

        db.commit()
        return processed_orders
