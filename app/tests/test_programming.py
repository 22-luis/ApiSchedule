"""
Tests for programming management endpoints.
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from datetime import datetime, date, timedelta
from app.models.programming import Programming, ProgrammingTask
from app.models.task import Task
from app.models.team import Team
from app.models.user import User

class TestProgramming:
    """Test programming management endpoints."""
    
    def test_get_programmings_success(self, client: TestClient, auth_headers: dict, test_programming: Programming):
        """Test getting all programmings."""
        response = client.get("/api/v1/programmings/", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1  # At least the test programming
        
        # Check programming structure
        for prog in data:
            assert "id" in prog
            assert "date" in prog
            assert "team_id" in prog
    
    def test_get_programmings_unauthorized(self, client: TestClient):
        """Test getting programmings without authentication."""
        response = client.get("/api/v1/programmings/")
        
        assert response.status_code == 401
    
    def test_get_programming_by_id_success(self, client: TestClient, auth_headers: dict, test_programming: Programming):
        """Test getting a specific programming by ID."""
        response = client.get(f"/api/v1/programmings/{test_programming.id}", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(test_programming.id)
        assert data["date"] == test_programming.date.isoformat()
        assert data["team_id"] == str(test_programming.team_id)
    
    def test_get_programming_by_id_not_found(self, client: TestClient, auth_headers: dict):
        """Test getting a non-existent programming."""
        import uuid
        fake_id = str(uuid.uuid4())
        response = client.get(f"/api/v1/programmings/{fake_id}", headers=auth_headers)
        
        assert response.status_code == 404
    
    def test_create_programming_success(self, client: TestClient, admin_auth_headers: dict, test_team: Team):
        """Test creating a new programming."""
        programming_data = {
            "date": date.today().isoformat(),
            "team_id": str(test_team.id)
        }
        
        response = client.post("/api/v1/programmings/", json=programming_data, headers=admin_auth_headers)
        
        assert response.status_code == 201
        data = response.json()
        assert data["date"] == date.today().isoformat()
        assert data["team_id"] == str(test_team.id)
        assert "id" in data
    
    def test_create_programming_unauthorized(self, client: TestClient, test_team: Team):
        """Test creating a programming without authentication."""
        programming_data = {
            "date": date.today().isoformat(),
            "team_id": str(test_team.id)
        }
        
        response = client.post("/api/v1/programmings/", json=programming_data)
        
        assert response.status_code == 401
    
    def test_create_programming_invalid_team(self, client: TestClient, admin_auth_headers: dict):
        """Test creating a programming with invalid team ID."""
        import uuid
        fake_team_id = str(uuid.uuid4())
        programming_data = {
            "date": date.today().isoformat(),
            "team_id": fake_team_id
        }
        
        response = client.post("/api/v1/programmings/", json=programming_data, headers=admin_auth_headers)
        
        assert response.status_code == 400
        data = response.json()
        assert "detail" in data
        assert "Team not found" in data["detail"]
    
    def test_create_programming_duplicate_date_team(self, client: TestClient, admin_auth_headers: dict, test_programming: Programming):
        """Test creating a programming with duplicate date and team."""
        programming_data = {
            "date": test_programming.date.isoformat(),
            "team_id": str(test_programming.team_id)
        }
        
        response = client.post("/api/v1/programmings/", json=programming_data, headers=admin_auth_headers)
        
        assert response.status_code == 400
        data = response.json()
        assert "detail" in data
        assert "Programming already exists" in data["detail"]
    
    def test_update_programming_success(self, client: TestClient, admin_auth_headers: dict, test_programming: Programming):
        """Test updating a programming."""
        new_date = (date.today() + timedelta(days=1)).isoformat()
        update_data = {
            "date": new_date
        }
        
        response = client.put(f"/api/v1/programmings/{test_programming.id}", json=update_data, headers=admin_auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["date"] == new_date
    
    def test_update_programming_unauthorized(self, client: TestClient, test_programming: Programming):
        """Test updating a programming without proper permissions."""
        update_data = {
            "date": date.today().isoformat()
        }
        
        response = client.put(f"/api/v1/programmings/{test_programming.id}", json=update_data)
        
        assert response.status_code == 401
    
    def test_update_programming_not_found(self, client: TestClient, admin_auth_headers: dict):
        """Test updating a non-existent programming."""
        import uuid
        fake_id = str(uuid.uuid4())
        update_data = {
            "date": date.today().isoformat()
        }
        
        response = client.put(f"/api/v1/programmings/{fake_id}", json=update_data, headers=admin_auth_headers)
        
        assert response.status_code == 404
    
    def test_delete_programming_success(self, client: TestClient, admin_auth_headers: dict, db: Session):
        """Test deleting a programming."""
        # Create a programming to delete
        programming = Programming(
            date=date.today(),
            team_id=None  # Will be set by fixture
        )
        db.add(programming)
        db.commit()
        db.refresh(programming)
        
        # Delete the programming
        response = client.delete(f"/api/v1/programmings/{programming.id}", headers=admin_auth_headers)
        
        assert response.status_code == 204
    
    def test_delete_programming_unauthorized(self, client: TestClient, test_programming: Programming):
        """Test deleting a programming without proper permissions."""
        response = client.delete(f"/api/v1/programmings/{test_programming.id}")
        
        assert response.status_code == 401
    
    def test_delete_programming_not_found(self, client: TestClient, admin_auth_headers: dict):
        """Test deleting a non-existent programming."""
        import uuid
        fake_id = str(uuid.uuid4())
        
        response = client.delete(f"/api/v1/programmings/{fake_id}", headers=admin_auth_headers)
        
        assert response.status_code == 404
    
    def test_get_programming_tasks(self, client: TestClient, auth_headers: dict, 
                                  test_programming: Programming, test_task: Task, db: Session):
        """Test getting programming tasks."""
        # Create programming task association
        programming_task = ProgrammingTask(
            programming_id=test_programming.id,
            task_id=test_task.id,
            order=1
        )
        db.add(programming_task)
        db.commit()
        
        response = client.get(f"/api/v1/programmings/{test_programming.id}/tasks", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        assert any(task["id"] == str(test_task.id) for task in data)
    
    def test_add_task_to_programming(self, client: TestClient, admin_auth_headers: dict, 
                                    test_programming: Programming, test_task: Task):
        """Test adding a task to a programming."""
        response = client.post(f"/api/v1/programmings/{test_programming.id}/tasks/{test_task.id}", 
                              headers=admin_auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "Task added to programming successfully" in data["message"]
    
    def test_remove_task_from_programming(self, client: TestClient, admin_auth_headers: dict, 
                                         test_programming: Programming, test_task: Task, db: Session):
        """Test removing a task from a programming."""
        # First add task to programming
        programming_task = ProgrammingTask(
            programming_id=test_programming.id,
            task_id=test_task.id,
            order=1
        )
        db.add(programming_task)
        db.commit()
        
        response = client.delete(f"/api/v1/programmings/{test_programming.id}/tasks/{test_task.id}", 
                                headers=admin_auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "Task removed from programming successfully" in data["message"]
    
    def test_reorder_programming_tasks(self, client: TestClient, admin_auth_headers: dict, 
                                      test_programming: Programming, test_task: Task, db: Session):
        """Test reordering programming tasks."""
        # Create programming task association
        programming_task = ProgrammingTask(
            programming_id=test_programming.id,
            task_id=test_task.id,
            order=1
        )
        db.add(programming_task)
        db.commit()
        
        reorder_data = {
            "task_orders": [
                {
                    "task_id": str(test_task.id),
                    "order": 2
                }
            ]
        }
        
        response = client.put(f"/api/v1/programmings/{test_programming.id}/reorder", 
                             json=reorder_data, headers=admin_auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "Tasks reordered successfully" in data["message"]
    
    def test_start_task_timer(self, client: TestClient, admin_auth_headers: dict, 
                             test_programming: Programming, test_task: Task, db: Session):
        """Test starting a task timer."""
        # Create programming task association
        programming_task = ProgrammingTask(
            programming_id=test_programming.id,
            task_id=test_task.id,
            order=1
        )
        db.add(programming_task)
        db.commit()
        
        response = client.post(f"/api/v1/programmings/{test_programming.id}/tasks/{test_task.id}/start", 
                              headers=admin_auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "Task timer started" in data["message"]
    
    def test_stop_task_timer(self, client: TestClient, admin_auth_headers: dict, 
                            test_programming: Programming, test_task: Task, db: Session):
        """Test stopping a task timer."""
        # Create programming task association with start time
        programming_task = ProgrammingTask(
            programming_id=test_programming.id,
            task_id=test_task.id,
            order=1,
            real_start_time=datetime.now()
        )
        db.add(programming_task)
        db.commit()
        
        response = client.post(f"/api/v1/programmings/{test_programming.id}/tasks/{test_task.id}/stop", 
                              headers=admin_auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "Task timer stopped" in data["message"]
    
    def test_get_programming_by_date_range(self, client: TestClient, auth_headers: dict, test_programming: Programming):
        """Test getting programmings by date range."""
        start_date = (date.today() - timedelta(days=7)).isoformat()
        end_date = (date.today() + timedelta(days=7)).isoformat()
        
        response = client.get(f"/api/v1/programmings/date-range?start_date={start_date}&end_date={end_date}", 
                             headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        assert any(prog["id"] == str(test_programming.id) for prog in data)
    
    def test_get_programming_by_team(self, client: TestClient, auth_headers: dict, test_programming: Programming, test_team: Team):
        """Test getting programmings by team."""
        response = client.get(f"/api/v1/programmings/team/{test_team.id}", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        assert any(prog["id"] == str(test_programming.id) for prog in data)
    
    def test_get_programming_report(self, client: TestClient, auth_headers: dict, 
                                   test_programming: Programming, test_task: Task, db: Session):
        """Test getting programming report."""
        # Create programming task association with completion data
        programming_task = ProgrammingTask(
            programming_id=test_programming.id,
            task_id=test_task.id,
            order=1,
            real_start_time=datetime.now(),
            real_end_time=datetime.now() + timedelta(hours=1),
            real_quantity=50,
            is_completed=True
        )
        db.add(programming_task)
        db.commit()
        
        response = client.get(f"/api/v1/programmings/{test_programming.id}/report", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert "programming_id" in data
        assert "date" in data
        assert "team_id" in data
        assert "tasks" in data
        assert "summary" in data
