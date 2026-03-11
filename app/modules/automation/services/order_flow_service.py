from typing import List, Dict

from sqlalchemy.orm import Session

from app.modules.orders.models import order as order_model
from app.modules.orders.models.state import OrderStatus
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
    ) -> Dict[str, List]:
        """
        Process Bin 8 (Packaging) orders:
        1. Find associated manufactured order OR pending fabrication order.
        2. Consume 'fabricated_quantity' (only if manufactured).
        3. Update manufactured order status if exhausted.
        4. Prepare order object for task creation (swap lote).
        
        Args:
            orders: List of bin 8 (packaging) orders to process
            db: Database session
            fabrication_orders_in_batch: Optional list of bin 10/100 orders being uploaded in the same batch
            
        Returns:
            Dict with 'processed' (successfully linked orders) and 'failed' (orders without a fabrication lot)
        """
        processed_orders = []
        failed_orders = []
        self_sufficient_orders = []
        
        # Track reserved quantities for fabrication orders (lote -> reserved_amount)
        reserved_quantities: Dict[int, float] = {}
        
        for order in orders:
            if order.bin != 8:
                continue

            logger.info(f"Processing Bin 8 order {order.lote} ({order.code})...")
            
            # CHECK IF ORDER ALREADY MANUALLY HAS ASSIGNED FABRICATION LOT
            if hasattr(order, '_usar_lote_fabricacion') and order._usar_lote_fabricacion:
                logger.info(
                    f"Order {order.lote} has manually assigned fabrication lot {order._usar_lote_fabricacion}. "
                    f"Skipping automatic matching."
                )
                # Order is already prepared for task creation with manual lot
                processed_orders.append(order)
                continue
            
            # 1. Find fabrication code
            fabrication_code = FabricationCodeFinder.find_fabrication_code(order.code, db)
            
            if not fabrication_code:
                # NEW: Check if this is a packaging-only order (no fabrication needed)
                # These orders use their own lote for packaging tasks
                logger.info(f"Order {order.lote} ({order.code}) has no fabrication code. Treating as packaging-only order.")
                order._usar_lote_fabricacion = order.lote # Use own lote
                order._original_packaging_lote = order.lote
                order._is_packaging_only = True
                order.status = OrderStatus.programmed
                db.add(order)
                processed_orders.append(order)
                continue

            # CHECK FOR SELF-SUFFICIENT ORDERS (e.g., mixed liquids that package themselves)
            if fabrication_code == order.code:
                 logger.info(f"Order {order.lote} is self-sufficient (Code == FabricationCode: {fabrication_code}). Skipping matching logic.")
                 self_sufficient_orders.append(order)
                 continue

            logger.info(f"Order {order.lote} ({order.code}) -> fabrication_code: {fabrication_code}")

            # Priority:
            # 1. Batch orders from the same file (most relevant - same upload)
            # 2. Manufactured orders in DB (already completed, ready to pack)
            # 3. Pending orders in DB (not yet manufactured)
            
            matched_order = None
            match_source = None

            # PASO 1: Buscar en el batch del mismo archivo (órdenes que vienen juntas)
            if fabrication_orders_in_batch:
                logger.debug(f"Searching in batch for fabrication_code={fabrication_code}...")
                for fab_order in fabrication_orders_in_batch:
                    current_reserved = reserved_quantities.get(fab_order.lote, 0.0)
                    available_qty = fab_order.quantity - current_reserved
                    
                    logger.debug(f"  Checking batch order {fab_order.lote}: code={fab_order.code}, qty={fab_order.quantity}, reserved={current_reserved}, available={available_qty}")
                    
                    if (fab_order.code == fabrication_code and 
                        available_qty >= order.quantity):
                        matched_order = fab_order
                        match_source = "batch"
                        logger.info(f"MATCHED: Found fabrication order {fab_order.lote} in same batch (Available: {available_qty}).")
                        break
                    else:
                        # Log why it didn't match
                        reasons = []
                        if fab_order.code != fabrication_code:
                            reasons.append(f"code mismatch ({fab_order.code} != {fabrication_code})")
                        if available_qty < order.quantity:
                            reasons.append(f"insufficient quantity ({available_qty} < {order.quantity})")
                        logger.debug(f"    Not matched: {', '.join(reasons)}")

            # PASO 2: Si no está en el batch, buscar orden YA FABRICADA en la BD
            if not matched_order:
                # Nota: Manufactured orders usan 'fabricated_quantity' que se actualiza directamente en DB, 
                # así que no necesitamos checkear reserved_quantities (o se asume que se commitea/flushea).
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
                # Obtenemos candidatos de la BD
                pending_candidates = db.query(order_model.Order).filter(
                    order_model.Order.code == fabrication_code,
                    order_model.Order.status.in_([OrderStatus.unprogrammed, OrderStatus.programmed, OrderStatus.weighed]),
                    order_model.Order.bin.in_([10, 100]),  # Solo órdenes de fabricación
                    order_model.Order.quantity >= order.quantity # Filtro inicial optimista
                ).order_by(order_model.Order.lote.asc()).limit(10).all() # Limitamos a 10 para no procesar demasiados
                
                for candidate in pending_candidates:
                    current_reserved = reserved_quantities.get(candidate.lote, 0.0)
                    available_qty = candidate.quantity - current_reserved
                    
                    if available_qty >= order.quantity:
                        matched_order = candidate
                        match_source = "pending_db"
                        logger.info(f"Found pending fabrication order {candidate.lote} in database (Available: {available_qty}).")
                        break
                    else:
                        logger.debug(f"Skipping pending candidate {candidate.lote}: insufficient available quantity ({available_qty} < {order.quantity})")

            # Si no encontramos nada, añadir a failed con información para selección manual
            if not matched_order:
                logger.warning(
                    f"No available fabrication order found for {order.code} "
                    f"(fabrication_code: {fabrication_code}, Req: {order.quantity}). Marking as failed for manual selection."
                )
                failed_orders.append({
                    "order": order,
                    "fabrication_code": fabrication_code,
                    "reason": "No se encontró lote de fabricación disponible con cantidad suficiente"
                })
                continue

            # Reservar la cantidad en el lote encontrado
            reserved_quantities[matched_order.lote] = reserved_quantities.get(matched_order.lote, 0.0) + order.quantity
            logger.info(f"Reserved {order.quantity} from lote {matched_order.lote} for packaging order {order.lote}. Total reserved: {reserved_quantities[matched_order.lote]}")

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

            # Update the packaging order status to program
            order.status = OrderStatus.programmed
            db.add(order)
            
            processed_orders.append(order)

        db.commit()
        return {
            "processed": processed_orders,
            "failed": failed_orders,
            "self_sufficient": self_sufficient_orders
        }
