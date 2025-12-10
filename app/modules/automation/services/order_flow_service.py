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

            logger.info(f"Order {order.lote} ({order.code}) -> fabrication_code: {fabrication_code}")

            # Priority:
            # 1. Batch orders from same file (most relevant - same upload)
            # 2. Manufactured orders in DB (already completed, ready to pack)
            # 3. Pending orders in DB (not yet manufactured)
            
            matched_order = None
            match_source = None

            # PASO 1: Buscar en el batch del mismo archivo (órdenes que vienen juntas)
            if fabrication_orders_in_batch:
                logger.info(f"Searching in batch for fabrication_code={fabrication_code}...")
                logger.info(f"Batch has {len(fabrication_orders_in_batch)} fabrication orders")
                for fab_order in fabrication_orders_in_batch:
                    logger.info(f"  Checking batch order {fab_order.lote}: code={fab_order.code}, qty={fab_order.quantity}")
                    if (fab_order.code == fabrication_code and 
                        fab_order.lote not in reserved_fabrication_lotes and
                        fab_order.quantity >= order.quantity):
                        matched_order = fab_order
                        match_source = "batch"
                        logger.info(f"MATCHED: Found fabrication order {fab_order.lote} in same batch.")
                        break
                    else:
                        # Log why it didn't match
                        reasons = []
                        if fab_order.code != fabrication_code:
                            reasons.append(f"code mismatch ({fab_order.code} != {fabrication_code})")
                        if fab_order.lote in reserved_fabrication_lotes:
                            reasons.append(f"lote {fab_order.lote} already reserved")
                        if fab_order.quantity < order.quantity:
                            reasons.append(f"insufficient quantity ({fab_order.quantity} < {order.quantity})")
                        logger.info(f"    Not matched: {', '.join(reasons)}")

            # PASO 2: Si no está en el batch, buscar orden YA FABRICADA en la BD
            if not matched_order:
                manufactured_order = db.query(order_model.Order).filter(
                    order_model.Order.code == fabrication_code,
                    order_model.Order.status == OrderStatus.manufactured,
                    order_model.Order.fabricated_quantity >= order.quantity
                ).order_by(
                    order_model.Order.fabricated_quantity.asc(),
                    order_model.Order.lote.asc()
                ).first()
                
                if manufactured_order:
                    matched_order = manufactured_order
                    match_source = "manufactured_db"
                    logger.info(f"Found manufactured order {manufactured_order.lote} in database with {manufactured_order.fabricated_quantity} available.")

            # PASO 3: Si no hay fabricada, buscar orden PENDIENTE en la BD
            if not matched_order:
                pending_fab_order = db.query(order_model.Order).filter(
                    order_model.Order.code == fabrication_code,
                    order_model.Order.status.in_([OrderStatus.unprogrammed, OrderStatus.programmed]),
                    order_model.Order.bin.in_([10, 100]),  # Solo órdenes de fabricación
                    order_model.Order.quantity >= order.quantity,
                    order_model.Order.lote.notin_(reserved_fabrication_lotes) if reserved_fabrication_lotes else True
                ).order_by(order_model.Order.lote.asc()).first()
                
                if pending_fab_order:
                    matched_order = pending_fab_order
                    match_source = "pending_db"
                    logger.info(f"Found pending fabrication order {pending_fab_order.lote} in database.")

            # Si no encontramos nada, skip
            if not matched_order:
                logger.warning(
                    f"No available fabrication order found for {order.code} "
                    f"(fabrication_code: {fabrication_code}, Req: {order.quantity}). Skipping."
                )
                continue

            # Reservar el lote encontrado
            reserved_fabrication_lotes.add(matched_order.lote)
            logger.info(f"Reserved lote {matched_order.lote} for packaging order {order.lote}")

            # Procesar según el tipo de match
            if match_source == "manufactured_db":
                # Consumir cantidad de la orden ya fabricada
                quantity_to_consume = order.quantity
                current_available = matched_order.fabricated_quantity
                
                new_available = current_available - quantity_to_consume
                matched_order.fabricated_quantity = max(0.0, new_available)
                
                # Status update logic removed to prevent premature "packaged" status.
                # Status will be updated by OrderStatusService when packaging tasks are completed.
                
                db.add(matched_order)
                db.flush()
                
                order._fabrication_was_already_manufactured = True
            else:
                # Es una orden del batch o pendiente - marcar como reservada
                if hasattr(matched_order, 'status') and matched_order.status == OrderStatus.unprogrammed:
                    matched_order.status = OrderStatus.programmed
                    db.add(matched_order)
                    logger.info(f"Marked fabrication order {matched_order.lote} as programmed (reserved).")
                
                order._fabrication_was_already_manufactured = False
                order._linked_fabrication_lote = matched_order.lote

            # Prepare for task creation
            order._usar_lote_fabricacion = matched_order.lote
            order._original_packaging_lote = order.lote
            
            logger.info(f"Packaging order {order.lote} linked to fabrication {matched_order.lote} (source: {match_source})")

            # Update the packaging order status to programmed
            order.status = OrderStatus.programmed
            db.add(order)
            
            processed_orders.append(order)

        db.commit()
        return processed_orders
