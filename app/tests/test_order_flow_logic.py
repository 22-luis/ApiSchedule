import pytest
from sqlalchemy.orm import Session
from app.modules.orders.models.order import Order
from app.modules.orders.models.state import OrderStatus
from app.modules.automation.services.order_flow_service import OrderFlowService
from app.modules.codes.models.code import Code
from datetime import date

def test_bin_8_consumption_logic(db: Session):
    # Setup: Create a Code with fabricationCode
    fab_code_str = "FAB-001"
    pack_code_str = "PACK-001"
    
    # Ensure codes exist (mocking or creating)
    # Check if they exist first to avoid unique constraint errors if re-running
    fab_code = db.query(Code).filter(Code.code == fab_code_str).first()
    if not fab_code:
        fab_code = Code(code=fab_code_str, description="Fabrication Code")
        db.add(fab_code)
    
    pack_code = db.query(Code).filter(Code.code == pack_code_str).first()
    if not pack_code:
        pack_code = Code(code=pack_code_str, description="Packaging Code", fabricationCode=fab_code_str)
        db.add(pack_code)
    else:
        pack_code.fabricationCode = fab_code_str
        db.add(pack_code)
        
    db.commit()

    # 1. Create a Manufactured Order (Bin 100)
    man_lote = 100001
    man_order = Order(
        lote=man_lote,
        code=fab_code_str,
        description="Manufactured Order",
        quantity=100.0,
        fabricated_quantity=100.0, # It was fully fabricated
        dueDate=date.today(),
        status=OrderStatus.manufactured,
        bin=100
    )
    db.add(man_order)
    db.commit()

    try:
        # 2. Create a Bin 8 Order (Quantity 40)
        pack_lote_1 = 800001
        pack_order_1 = Order(
            lote=pack_lote_1,
            code=pack_code_str,
            description="Packaging Order 1",
            quantity=40.0,
            dueDate=date.today(),
            status=OrderStatus.unprogrammed,
            bin=8
        )
        db.add(pack_order_1)
        db.commit()

        # 3. Process Bin 8 Order
        result = OrderFlowService.process_bin_8_orders([pack_order_1], db)
        processed = result["processed"]
        
        # Verify
        db.refresh(man_order)
        db.refresh(pack_order_1)
        
        assert len(processed) == 1
        assert pack_order_1._usar_lote_fabricacion == man_lote
        assert man_order.fabricated_quantity == 60.0 # 100 - 40
        assert man_order.status == OrderStatus.manufactured # Still has quantity

        # 4. Create another Bin 8 Order (Quantity 60)
        pack_lote_2 = 800002
        pack_order_2 = Order(
            lote=pack_lote_2,
            code=pack_code_str,
            description="Packaging Order 2",
            quantity=60.0,
            dueDate=date.today(),
            status=OrderStatus.unprogrammed,
            bin=8
        )
        db.add(pack_order_2)
        db.commit()

        # 5. Process Second Bin 8 Order
        result_2 = OrderFlowService.process_bin_8_orders([pack_order_2], db)
        processed_2 = result_2["processed"]
        
        # Verify
        db.refresh(man_order)
        db.refresh(pack_order_2)
        
        assert len(processed_2) == 1
        assert pack_order_2._usar_lote_fabricacion == man_lote
        assert man_order.fabricated_quantity == 0.0 # 60 - 60
        # assert man_order.status == OrderStatus.packaged # Exhausted
        # Status update logic was removed from OrderFlowService and moved to OrderStatusService (on task completion)
        assert man_order.status == OrderStatus.manufactured 

    finally:
        # Cleanup
        lotes_to_delete = [man_lote]
        if 'pack_lote_1' in locals(): lotes_to_delete.append(pack_lote_1)
        if 'pack_lote_2' in locals(): lotes_to_delete.append(pack_lote_2)
        
        db.query(Order).filter(Order.lote.in_(lotes_to_delete)).delete(synchronize_session=False)
        # We don't delete codes as they might be used by other tests or system
        db.commit()
