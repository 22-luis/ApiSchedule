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
    def process_bin_8_orders(
        orders: List[order_model.Order], 
        db: Session,
        fabrication_orders_in_batch: List[order_model.Order] = None
    ) -> List[order_model.Order]:
        """
        Process Bin 8 (Packaging) orders:
        1. Find associated manufactured order OR pending fabrication order.
        2. Consume 'fabricated_quantity' (only if manufactured).
        3. Update manufactured order status if exhausted.
        4. Prepare order object for task creation (swap lote).
        
        Args:
            orders: List of bin 8 (packaging) orders to process
            db: Database session
            fabrication_orders_in_batch: Optional list of bin 10/100 orders being uploaded in same batch
        """
        processed_orders = []
        
        # Track which fabrication orders have been reserved (both from DB and batch)
        reserved_fabrication_lotes = set()
        
        for order in orders:
            if order.bin != 8:
                continue

            logger.info(f"Processing Bin 8 order {order.lote} ({order.code})...")
            
            # 1. Find fabrication code
            fabrication_code = FabricationCodeFinder.find_fabrication_code(order.code, db)
            
            if not fabrication_code:
                logger.warning(f"Could not find fabrication code for order {order.lote} ({order.code}). Skipping.")
                continue

            # 2. PRIMERO: Buscar orden ya fabricada (manufactured)
            manufactured_order = db.query(order_model.Order).filter(
                order_model.Order.code == fabrication_code,
                order_model.Order.status == OrderStatus.manufactured,
                order_model.Order.fabricated_quantity >= order.quantity,
                order_model.Order.lote.notin_(reserved_fabrication_lotes) if reserved_fabrication_lotes else True
            ).order_by(order_model.Order.lote.asc()).first()

            if manufactured_order:
                # Usar orden ya fabricada (comportamiento existente)
                logger.info(f"Found manufactured order {manufactured_order.lote} with {manufactured_order.fabricated_quantity} available.")

                # Reserve this lote
                reserved_fabrication_lotes.add(manufactured_order.lote)

                # Consume quantity
                quantity_to_consume = order.quantity
                current_available = manufactured_order.fabricated_quantity
                
                new_available = current_available - quantity_to_consume
                manufactured_order.fabricated_quantity = max(0.0, new_available)
                
                # Update status if exhausted
                if manufactured_order.fabricated_quantity <= 0:
                    manufactured_order.status = OrderStatus.packaged
                    logger.info(f"Manufactured order {manufactured_order.lote} exhausted. Status changed to 'packaged'.")
                
                db.add(manufactured_order)
                db.flush()
                
                # Prepare for task creation
                order._usar_lote_fabricacion = manufactured_order.lote
                order._original_packaging_lote = order.lote
                order._fabrication_was_already_manufactured = True
                
            else:
                # 3. NUEVO: Buscar órdenes de fabricación pendientes (unprogrammed o programmed)
                # Primero en el batch pasado, luego en la BD
                matching_order = None
                
                # 3a. Buscar en el batch pasado (si existe)
                if fabrication_orders_in_batch:
                    for fab_order in fabrication_orders_in_batch:
                        if (fab_order.code == fabrication_code and 
                            fab_order.lote not in reserved_fabrication_lotes and
                            fab_order.quantity >= order.quantity):
                            matching_order = fab_order
                            logger.info(f"Found pending fabrication order {fab_order.lote} in same batch.")
                            break
                
                # 3b. Si no está en el batch, buscar en la BD órdenes pendientes
                if not matching_order:
                    pending_fab_order = db.query(order_model.Order).filter(
                        order_model.Order.code == fabrication_code,
                        order_model.Order.status.in_([OrderStatus.unprogrammed, OrderStatus.programmed]),
                        order_model.Order.bin.in_([10, 100]),  # Solo órdenes de fabricación
                        order_model.Order.quantity >= order.quantity,
                        order_model.Order.lote.notin_(reserved_fabrication_lotes) if reserved_fabrication_lotes else True
                    ).order_by(order_model.Order.lote.asc()).first()
                    
                    if pending_fab_order:
                        matching_order = pending_fab_order
                        logger.info(f"Found pending fabrication order {pending_fab_order.lote} in database.")
                
                if matching_order:
                    # Reservar esta orden de fabricación
                    reserved_fabrication_lotes.add(matching_order.lote)
                    
                    # Marcar la orden de fabricación como reservada (si no lo está ya)
                    if matching_order.status == OrderStatus.unprogrammed:
                        matching_order.status = OrderStatus.programmed
                        db.add(matching_order)
                        logger.info(f"Marked fabrication order {matching_order.lote} as programmed (reserved).")
                    
                    # Prepare for task creation usando el lote de fabricación pendiente
                    order._usar_lote_fabricacion = matching_order.lote
                    order._original_packaging_lote = order.lote
                    order._fabrication_was_already_manufactured = False
                    order._linked_fabrication_lote = matching_order.lote
                    
                    logger.info(f"Packaging order {order.lote} linked to pending fabrication {matching_order.lote}")
                else:
                    logger.warning(
                        f"No available manufactured or pending fabrication order found for "
                        f"{order.code} (fabrication_code: {fabrication_code}, Req: {order.quantity}). Skipping."
                    )
                    continue

            # Update the packaging order status to programmed
            order.status = OrderStatus.programmed
            db.add(order)
            
            processed_orders.append(order)

        db.commit()
        return processed_orders
