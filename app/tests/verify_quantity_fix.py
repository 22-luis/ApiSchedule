import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.modules.programming.models.programming import Programming, ProgrammingTask
from app.modules.programming.models.task import Task
from app.modules.organization.models.team import Team

def test_update_task_real_quantity_success(client: TestClient, admin_auth_headers: dict, 
                                        test_programming: Programming, test_task: Task, db: Session):
    """Test updating task real quantity in a programming."""
    # Create association
    pt = ProgrammingTask(
        programming_id=test_programming.id,
        task_id=test_task.id,
        order=1
    )
    db.add(pt)
    db.commit()
    
    url = f"/api/v1/programmings/{test_programming.id}/tasks/{test_task.id}/quantity"
    payload = {"real_quantity": 75.5}
    
    response = client.patch(url, json=payload, headers=admin_auth_headers)
    
    assert response.status_code == 200
    # Verify in DB
    db.refresh(pt)
    assert pt.real_quantity == 75.5

def test_toggle_task_status_success(client: TestClient, admin_auth_headers: dict, 
                                 test_programming: Programming, test_task: Task, db: Session):
    """Test toggling task status in a programming."""
    # Create association
    pt = ProgrammingTask(
        programming_id=test_programming.id,
        task_id=test_task.id,
        order=1,
        is_completed=False
    )
    db.add(pt)
    db.commit()
    
    url = f"/api/v1/programmings/{test_programming.id}/tasks/{test_task.id}/toggle_status"
    payload = {
        "assigned_quantity": 120.0,
        "real_quantity": 115.0
    }
    
    response = client.post(url, json=payload, headers=admin_auth_headers)
    
    assert response.status_code == 200
    
    # Verify in DB
    db.refresh(pt)
    db.refresh(test_task)
    
    assert pt.is_completed is True
    assert pt.real_quantity == 115.0
    assert test_task.quantity == 120.0
    assert test_task.is_completed is True
    assert test_task.status == "completada"

def test_update_task_real_quantity_not_found(client: TestClient, admin_auth_headers: dict):
    """Test updating quantity for non-existent programming/task combo."""
    import uuid
    p_id = uuid.uuid4()
    t_id = uuid.uuid4()
    
    url = f"/api/v1/programmings/{p_id}/tasks/{t_id}/quantity"
    response = client.patch(url, json={"real_quantity": 10}, headers=admin_auth_headers)
    
    assert response.status_code == 404
