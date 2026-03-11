import pytest
from sqlalchemy.orm import Session
from app.modules.orders.models.order import Order
from app.modules.programming.models.task import Task
from app.modules.programming.models.programming import Programming, ProgrammingTask
from app.modules.orders.models.state import OrderStatus
from app.shared.utils.business.order_status_service import OrderStatusService
from datetime import date, datetime

def test_fabricated_quantity_update(db: Session):
    # 1. Create a test order
    test_lote = 999999
    order = Order(
        lote=test_lote,
        description="Test Order for Fabricated Quantity",
        quantity=100.0,
        dueDate=date.today(),
        status=OrderStatus.programmed,
        bin=1
    )
    db.add(order)
    db.commit()

    try:
        # 2. Create a task linked to this order
        task = Task(
            lote=str(test_lote),
            activity="FABRICADO",
            description="Fabrication Task",
            quantity=100.0
        )
        db.add(task)
        db.flush()

        # 3. Create a programming and programming task
        # Fetch an existing team
        from app.modules.organization.models.team import Team
        team = db.query(Team).first()
        if not team:
            # Create a dummy team if none exists
            team = Team(name="Test Team")
            db.add(team)
            db.commit()
            
        programming = Programming(
            date=date.today(),
            team_id=team.id
        )
        db.add(programming)
        db.commit()

        prog_task = ProgrammingTask(
            programming_id=programming.id,
            task_id=task.id,
            real_quantity=85.5,
            is_completed=True,
            order=1
        )
        db.add(prog_task)
        db.commit()
        # The service method accesses programming_task.task.lote
        prog_task.task = task

        # 4. Call the service method
        OrderStatusService.update_order_status_for_task_completion(db, prog_task)
        
        # 5. Verify
        db.refresh(order)
        print(f"Order Status: {order.status}")
        print(f"Fabricated Quantity: {order.fabricated_quantity}")
        
        assert order.status == OrderStatus.manufactured
        assert order.fabricated_quantity == 85.5

    finally:
        # Cleanup
        db.delete(order)
        db.commit()
