"""
Tests for task management endpoints.
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from app.models.task import Task
from app.models.team import Team
from app.models.programming import Programming, ProgrammingTask
from app.models.code import Code
from app.models.preparation import Preparation
from app.models.user import User

class TestTasks:
    """Test task management endpoints."""
    
    def test_get_tasks_success(self, client: TestClient, auth_headers: dict, test_task: Task):
        """Test getting all tasks."""
        response = client.get("/api/v1/tasks/", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1  # At least the test task
        
        # Check task structure
        for task in data:
            assert "id" in task
            assert "lote" in task
            assert "quantity" in task
            assert "specification" in task
    
    def test_get_tasks_unauthorized(self, client: TestClient):
        """Test getting tasks without authentication."""
        response = client.get("/api/v1/tasks/")
        
        assert response.status_code == 401
    
    def test_get_task_by_id_success(self, client: TestClient, auth_headers: dict, test_task: Task):
        """Test getting a specific task by ID."""
        response = client.get(f"/api/v1/tasks/{test_task.id}", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(test_task.id)
        assert data["lote"] == test_task.lote
        assert data["quantity"] == test_task.quantity
    
    def test_get_task_by_id_not_found(self, client: TestClient, auth_headers: dict):
        """Test getting a non-existent task."""
        import uuid
        fake_id = str(uuid.uuid4())
        response = client.get(f"/api/v1/tasks/{fake_id}", headers=auth_headers)
        
        assert response.status_code == 404
    
    def test_create_task_success(self, client: TestClient, admin_auth_headers: dict, 
                                test_team: Team, test_programming: Programming, 
                                test_code: Code, test_preparation: Preparation):
        """Test creating a new task."""
        task_data = {
            "total_time": 120,
            "minutes": 120,
            "start_time": datetime.now().isoformat(),
            "end_time": (datetime.now() + timedelta(hours=2)).isoformat(),
            "teamIds": [str(test_team.id)],
            "programming_id": str(test_programming.id),
            "code_id": str(test_code.id),
            "lote": "TEST123",
            "quantity": 50,
            "specification": "Test specification",
            "preparation_id": str(test_preparation.id),
            "people": 3,
            "performance": 0.9,
            "material": "Test material",
            "presentation": "Test presentation",
            "fabricationCode": "FAB123",
            "usefulLife": "30 days",
            "related_task_code": "REL123",
            "unit": "kg",
            "type": "production",
            "activity": "manufacturing",
            "description": "Test task description"
        }
        
        response = client.post("/api/v1/tasks/", json=task_data, headers=admin_auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["lote"] == "TEST123"
        assert data["quantity"] == 50
        assert data["specification"] == "Test specification"
        assert "id" in data
        assert "created_by_user_id" in data
    
    def test_create_task_unauthorized(self, client: TestClient, test_team: Team, test_programming: Programming):
        """Test creating a task without authentication."""
        task_data = {
            "total_time": 120,
            "minutes": 120,
            "start_time": datetime.now().isoformat(),
            "end_time": (datetime.now() + timedelta(hours=2)).isoformat(),
            "teamIds": [str(test_team.id)],
            "programming_id": str(test_programming.id),
            "lote": "TEST123",
            "quantity": 50,
            "specification": "Test specification"
        }
        
        response = client.post("/api/v1/tasks/", json=task_data)
        
        assert response.status_code == 401
    
    def test_create_task_invalid_teams(self, client: TestClient, admin_auth_headers: dict, test_programming: Programming):
        """Test creating a task with invalid team IDs."""
        import uuid
        fake_team_id = str(uuid.uuid4())
        task_data = {
            "total_time": 120,
            "minutes": 120,
            "start_time": datetime.now().isoformat(),
            "end_time": (datetime.now() + timedelta(hours=2)).isoformat(),
            "teamIds": [fake_team_id],
            "programming_id": str(test_programming.id),
            "lote": "TEST123",
            "quantity": 50,
            "specification": "Test specification"
        }
        
        response = client.post("/api/v1/tasks/", json=task_data, headers=admin_auth_headers)
        
        assert response.status_code == 400
        data = response.json()
        assert "detail" in data
        assert "One or more teams not found" in data["detail"]
    
    def test_create_task_invalid_programming(self, client: TestClient, admin_auth_headers: dict, test_team: Team):
        """Test creating a task with invalid programming ID."""
        import uuid
        fake_programming_id = str(uuid.uuid4())
        task_data = {
            "total_time": 120,
            "minutes": 120,
            "start_time": datetime.now().isoformat(),
            "end_time": (datetime.now() + timedelta(hours=2)).isoformat(),
            "teamIds": [str(test_team.id)],
            "programming_id": fake_programming_id,
            "lote": "TEST123",
            "quantity": 50,
            "specification": "Test specification"
        }
        
        response = client.post("/api/v1/tasks/", json=task_data, headers=admin_auth_headers)
        
        assert response.status_code == 404
        data = response.json()
        assert "detail" in data
        assert "Programming not found" in data["detail"]
    
    def test_update_task_success(self, client: TestClient, admin_auth_headers: dict, test_task: Task):
        """Test updating a task."""
        update_data = {
            "lote": "UPDATED123",
            "quantity": 75,
            "specification": "Updated specification"
        }
        
        response = client.put(f"/api/v1/tasks/{test_task.id}", json=update_data, headers=admin_auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["lote"] == "UPDATED123"
        assert data["quantity"] == 75
        assert data["specification"] == "Updated specification"
    
    def test_update_task_unauthorized(self, client: TestClient, test_task: Task):
        """Test updating a task without proper permissions."""
        update_data = {
            "lote": "UNAUTHORIZED123"
        }
        
        response = client.put(f"/api/v1/tasks/{test_task.id}", json=update_data)
        
        assert response.status_code == 401
    
    def test_update_task_not_found(self, client: TestClient, admin_auth_headers: dict):
        """Test updating a non-existent task."""
        import uuid
        fake_id = str(uuid.uuid4())
        update_data = {
            "lote": "UPDATED123"
        }
        
        response = client.put(f"/api/v1/tasks/{fake_id}", json=update_data, headers=admin_auth_headers)
        
        assert response.status_code == 404
    
    def test_delete_task_success(self, client: TestClient, admin_auth_headers: dict, db: Session):
        """Test deleting a task."""
        # Create a task to delete
        task = Task(
            lote="TASK_TO_DELETE",
            quantity=100,
            specification="Task to delete"
        )
        db.add(task)
        db.commit()
        db.refresh(task)
        
        # Delete the task
        response = client.delete(f"/api/v1/tasks/{task.id}", headers=admin_auth_headers)
        
        assert response.status_code == 204
    
    def test_delete_task_unauthorized(self, client: TestClient, test_task: Task):
        """Test deleting a task without proper permissions."""
        response = client.delete(f"/api/v1/tasks/{test_task.id}")
        
        assert response.status_code == 401
    
    def test_delete_task_not_found(self, client: TestClient, admin_auth_headers: dict):
        """Test deleting a non-existent task."""
        import uuid
        fake_id = str(uuid.uuid4())
        
        response = client.delete(f"/api/v1/tasks/{fake_id}", headers=admin_auth_headers)
        
        assert response.status_code == 404
    
    def test_duplicate_task_success(self, client: TestClient, admin_auth_headers: dict, 
                                   test_task: Task, test_programming: Programming, db: Session):
        """Test duplicating a task."""
        # Create programming task association
        programming_task = ProgrammingTask(
            programming_id=test_programming.id,
            task_id=test_task.id,
            order=1
        )
        db.add(programming_task)
        db.commit()
        
        duplicate_data = {
            "lote": "DUPLICATE123"
        }
        
        response = client.post(f"/api/v1/tasks/{test_task.id}/duplicate", 
                              json=duplicate_data, headers=admin_auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["lote"] == "DUPLICATE123"
        assert data["quantity"] == test_task.quantity
        assert data["specification"] == test_task.specification
        assert data["id"] != str(test_task.id)  # Should be a new task
    
    def test_duplicate_task_not_found(self, client: TestClient, admin_auth_headers: dict):
        """Test duplicating a non-existent task."""
        import uuid
        fake_id = str(uuid.uuid4())
        duplicate_data = {
            "lote": "DUPLICATE123"
        }
        
        response = client.post(f"/api/v1/tasks/{fake_id}/duplicate", 
                              json=duplicate_data, headers=admin_auth_headers)
        
        assert response.status_code == 404
    
    def test_get_task_programmings(self, client: TestClient, auth_headers: dict, 
                                  test_task: Task, test_programming: Programming, db: Session):
        """Test getting task programmings."""
        # Create programming task association
        programming_task = ProgrammingTask(
            programming_id=test_programming.id,
            task_id=test_task.id,
            order=1
        )
        db.add(programming_task)
        db.commit()
        
        response = client.get(f"/api/v1/tasks/{test_task.id}/programmings", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        assert any(prog["id"] == str(test_programming.id) for prog in data)
    
    def test_get_task_teams(self, client: TestClient, auth_headers: dict, 
                           test_task: Task, test_team: Team, db: Session):
        """Test getting task teams."""
        # Add team to task
        test_task.teams.append(test_team)
        db.commit()
        
        response = client.get(f"/api/v1/tasks/{test_task.id}/teams", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        assert any(team["id"] == str(test_team.id) for team in data)
    
    def test_add_team_to_task(self, client: TestClient, admin_auth_headers: dict, 
                             test_task: Task, test_team: Team):
        """Test adding a team to a task."""
        response = client.post(f"/api/v1/tasks/{test_task.id}/teams/{test_team.id}", 
                              headers=admin_auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "Team added to task successfully" in data["message"]
    
    def test_remove_team_from_task(self, client: TestClient, admin_auth_headers: dict, 
                                  test_task: Task, test_team: Team, db: Session):
        """Test removing a team from a task."""
        # First add team to task
        test_task.teams.append(test_team)
        db.commit()
        
        response = client.delete(f"/api/v1/tasks/{test_task.id}/teams/{test_team.id}", 
                                headers=admin_auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "Team removed from task successfully" in data["message"]
