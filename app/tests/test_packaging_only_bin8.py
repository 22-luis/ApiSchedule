import pytest
from sqlalchemy.orm import Session
from app.modules.orders.models.order import Order
from app.modules.orders.models.state import OrderStatus
from app.modules.automation.services.order_flow_service import OrderFlowService
from app.modules.codes.models.code import Code
from datetime import date

def test_packaging_only_bin_8_logic(db: Session):
    # Setup: Create a Code WITHOUT fabricationCode
    pack_code_str = "PACK-ONLY-001"
    
    pack_code = db.query(Code).filter(Code.code == pack_code_str).first()
    if not pack_code:
        pack_code = Code(code=pack_code_str, description="Packaging Only Code", fabricationCode=None)
        db.add(pack_code)
    else:
        pack_code.fabricationCode = None
        db.add(pack_code)
        
    db.commit()

    pack_lote = 899999
    try:
        # 1. Create a Bin 8 Order
        pack_order = Order(
            lote=pack_lote,
            code=pack_code_str,
            description="Packaging Only Order",
            quantity=50.0,
            dueDate=date.today(),
            status=OrderStatus.unprogrammed,
            bin=8
        )
        db.add(pack_order)
        db.commit()

        # 2. Process Bin 8 Order
        result = OrderFlowService.process_bin_8_orders([pack_order], db)
        
        # Verify
        db.refresh(pack_order)
        
        assert len(result["processed"]) == 1
        assert pack_order._usar_lote_fabricacion == pack_lote
        assert pack_order._is_packaging_only == True
        assert pack_order.status == OrderStatus.programmed

    finally:
        # Cleanup
        db.query(Order).filter(Order.lote == pack_lote).delete(synchronize_session=False)
        db.commit()
