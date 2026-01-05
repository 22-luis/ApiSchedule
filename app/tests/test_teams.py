"""
Tests for team management endpoints.
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.modules.core.models.team import Team
from app.modules.core.models.user import User
from app.modules.programming.models.task import Task
from app.modules.codes.models.code import Code

class TestTeams:
    """Test team management endpoints."""
    
    def test_get_teams_success(self, client: TestClient, auth_headers: dict, test_team: Team):
        """Test getting all teams."""
        response = client.get("/api/v1/teams/", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1  # At least the test team
        
        # Check team structure
        for team in data:
            assert "id" in team
            assert "name" in team
            assert "supervisorId" in team
    
    def test_get_teams_unauthorized(self, client: TestClient):
        """Test getting teams without authentication."""
        response = client.get("/api/v1/teams/")
        
        assert response.status_code == 401
    
    def test_get_team_by_id_success(self, client: TestClient, auth_headers: dict, test_team: Team):
        """Test getting a specific team by ID."""
        response = client.get(f"/api/v1/teams/{test_team.id}", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(test_team.id)
        assert data["name"] == test_team.name
        assert data["supervisorId"] == str(test_team.supervisorId)
    
    def test_get_team_by_id_not_found(self, client: TestClient, auth_headers: dict):
        """Test getting a non-existent team."""
        import uuid
        fake_id = str(uuid.uuid4())
        response = client.get(f"/api/v1/teams/{fake_id}", headers=auth_headers)
        
        assert response.status_code == 404
    
    def test_create_team_success(self, client: TestClient, admin_auth_headers: dict, test_supervisor: User):
        """Test creating a new team."""
        team_data = {
            "name": "New Test Team",
            "supervisorId": str(test_supervisor.id)
        }
        
        response = client.post("/api/v1/teams/", json=team_data, headers=admin_auth_headers)
        
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "New Test Team"
        assert data["supervisorId"] == str(test_supervisor.id)
        assert "id" in data
    
    def test_create_team_unauthorized(self, client: TestClient, test_supervisor: User):
        """Test creating a team without proper permissions."""
        team_data = {
            "name": "Unauthorized Team",
            "supervisorId": str(test_supervisor.id)
        }
        
        response = client.post("/api/v1/teams/", json=team_data)
        
        assert response.status_code == 401
    
    def test_create_team_invalid_supervisor(self, client: TestClient, admin_auth_headers: dict):
        """Test creating a team with invalid supervisor ID."""
        import uuid
        fake_supervisor_id = str(uuid.uuid4())
        team_data = {
            "name": "Invalid Supervisor Team",
            "supervisorId": fake_supervisor_id
        }
        
        response = client.post("/api/v1/teams/", json=team_data, headers=admin_auth_headers)
        
        assert response.status_code == 400
        data = response.json()
        assert "detail" in data
        assert "Supervisor not found" in data["detail"]
    
    def test_update_team_success(self, client: TestClient, admin_auth_headers: dict, test_team: Team, test_supervisor: User):
        """Test updating a team."""
        update_data = {
            "name": "Updated Team Name",
            "supervisorId": str(test_supervisor.id)
        }
        
        response = client.put(f"/api/v1/teams/{test_team.id}", json=update_data, headers=admin_auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Team Name"
        assert data["supervisorId"] == str(test_supervisor.id)
    
    def test_update_team_unauthorized(self, client: TestClient, test_team: Team):
        """Test updating a team without proper permissions."""
        update_data = {
            "name": "Unauthorized Update"
        }
        
        response = client.put(f"/api/v1/teams/{test_team.id}", json=update_data)
        
        assert response.status_code == 401
    
    def test_update_team_not_found(self, client: TestClient, admin_auth_headers: dict):
        """Test updating a non-existent team."""
        import uuid
        fake_id = str(uuid.uuid4())
        update_data = {
            "name": "Updated Name"
        }
        
        response = client.put(f"/api/v1/teams/{fake_id}", json=update_data, headers=admin_auth_headers)
        
        assert response.status_code == 404
    
    def test_delete_team_success(self, client: TestClient, admin_auth_headers: dict, db: Session):
        """Test deleting a team."""
        # Create a team to delete
        team_data = {
            "name": "Team to Delete",
            "supervisorId": None
        }
        
        create_response = client.post("/api/v1/teams/", json=team_data, headers=admin_auth_headers)
        assert create_response.status_code == 201
        team_id = create_response.json()["id"]
        
        # Delete the team
        response = client.delete(f"/api/v1/teams/{team_id}", headers=admin_auth_headers)
        
        assert response.status_code == 204
    
    def test_delete_team_unauthorized(self, client: TestClient, test_team: Team):
        """Test deleting a team without proper permissions."""
        response = client.delete(f"/api/v1/teams/{test_team.id}")
        
        assert response.status_code == 401
    
    def test_delete_team_not_found(self, client: TestClient, admin_auth_headers: dict):
        """Test deleting a non-existent team."""
        import uuid
        fake_id = str(uuid.uuid4())
        
        response = client.delete(f"/api/v1/teams/{fake_id}", headers=admin_auth_headers)
        
        assert response.status_code == 404
    
    def test_get_team_users(self, client: TestClient, auth_headers: dict, test_team: Team, test_user: User, db: Session):
        """Test getting team users."""
        # Add user to team
        test_team.users.append(test_user)
        db.commit()
        
        response = client.get(f"/api/v1/teams/{test_team.id}/users", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        assert any(user["id"] == str(test_user.id) for user in data)
    
    def test_get_team_tasks(self, client: TestClient, auth_headers: dict, test_team: Team, test_task: Task, db: Session):
        """Test getting team tasks."""
        # Add task to team
        test_team.tasks.append(test_task)
        db.commit()
        
        response = client.get(f"/api/v1/teams/{test_team.id}/tasks", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        assert any(task["id"] == str(test_task.id) for task in data)
    
    def test_get_team_codes(self, client: TestClient, auth_headers: dict, test_team: Team, test_code: Code, db: Session):
        """Test getting team codes."""
        # Add code to team
        test_team.codes.append(test_code)
        db.commit()
        
        response = client.get(f"/api/v1/teams/{test_team.id}/codes", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        assert any(code["id"] == str(test_code.id) for code in data)
    
    def test_add_user_to_team(self, client: TestClient, admin_auth_headers: dict, test_team: Team, test_user: User):
        """Test adding a user to a team."""
        response = client.post(f"/api/v1/teams/{test_team.id}/users/{test_user.id}", headers=admin_auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "User added to team successfully" in data["message"]
    
    def test_remove_user_from_team(self, client: TestClient, admin_auth_headers: dict, test_team: Team, test_user: User, db: Session):
        """Test removing a user from a team."""
        # First add user to team
        test_team.users.append(test_user)
        db.commit()
        
        response = client.delete(f"/api/v1/teams/{test_team.id}/users/{test_user.id}", headers=admin_auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "User removed from team successfully" in data["message"]
    
    def test_add_task_to_team(self, client: TestClient, admin_auth_headers: dict, test_team: Team, test_task: Task):
        """Test adding a task to a team."""
        response = client.post(f"/api/v1/teams/{test_team.id}/tasks/{test_task.id}", headers=admin_auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "Task added to team successfully" in data["message"]
    
    def test_remove_task_from_team(self, client: TestClient, admin_auth_headers: dict, test_team: Team, test_task: Task, db: Session):
        """Test removing a task from a team."""
        # First add task to team
        test_team.tasks.append(test_task)
        db.commit()
        
        response = client.delete(f"/api/v1/teams/{test_team.id}/tasks/{test_task.id}", headers=admin_auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "Task removed from team successfully" in data["message"]
    
    def test_add_code_to_team(self, client: TestClient, admin_auth_headers: dict, test_team: Team, test_code: Code):
        """Test adding a code to a team."""
        response = client.post(f"/api/v1/teams/{test_team.id}/codes/{test_code.id}", headers=admin_auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "Code added to team successfully" in data["message"]
    
    def test_remove_code_from_team(self, client: TestClient, admin_auth_headers: dict, test_team: Team, test_code: Code, db: Session):
        """Test removing a code from a team."""
        # First add code to team
        test_team.codes.append(test_code)
        db.commit()
        
        response = client.delete(f"/api/v1/teams/{test_team.id}/codes/{test_code.id}", headers=admin_auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "Code removed from team successfully" in data["message"]
