"""
Tests for user management endpoints.
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.modules.organization.models.user import User
from app.modules.organization.models.team import Team
from app.modules.organization.models.role import UserRole

class TestUsers:
    """Test user management endpoints."""
    
    def test_get_users_admin_access(self, client: TestClient, admin_auth_headers: dict, test_user: User):
        """Test getting all users with admin access."""
        response = client.get("/api/v1/users/", headers=admin_auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1  # At least the test user
        
        # Check that passwords are not included
        for user in data:
            assert "password" not in user
            assert "id" in user
            assert "username" in user
            assert "role" in user
    
    def test_get_users_unauthorized(self, client: TestClient):
        """Test getting users without authentication."""
        response = client.get("/api/v1/users/")
        
        assert response.status_code == 401
    
    def test_get_users_insufficient_permissions(self, client: TestClient, auth_headers: dict):
        """Test getting users with insufficient permissions."""
        response = client.get("/api/v1/users/", headers=auth_headers)
        
        assert response.status_code == 403
    
    def test_get_user_by_id_admin(self, client: TestClient, admin_auth_headers: dict, test_user: User):
        """Test getting a specific user by ID with admin access."""
        response = client.get(f"/api/v1/users/{test_user.id}", headers=admin_auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(test_user.id)
        assert data["username"] == test_user.username
        assert data["role"] == test_user.role.value
        assert "password" not in data
    
    def test_get_user_by_id_own_profile(self, client: TestClient, auth_headers: dict, test_user: User):
        """Test getting own user profile."""
        response = client.get(f"/api/v1/users/{test_user.id}", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(test_user.id)
        assert data["username"] == test_user.username
    
    def test_get_user_by_id_other_user_unauthorized(self, client: TestClient, auth_headers: dict, test_admin: User):
        """Test getting another user's profile without proper permissions."""
        response = client.get(f"/api/v1/users/{test_admin.id}", headers=auth_headers)
        
        assert response.status_code == 403
    
    def test_get_user_by_id_not_found(self, client: TestClient, admin_auth_headers: dict):
        """Test getting a non-existent user."""
        import uuid
        fake_id = str(uuid.uuid4())
        response = client.get(f"/api/v1/users/{fake_id}", headers=admin_auth_headers)
        
        assert response.status_code == 404
    
    def test_create_user_admin(self, client: TestClient, admin_auth_headers: dict):
        """Test creating a new user with admin access."""
        user_data = {
            "username": "newuser",
            "password": "newpassword123",
            "role": "USER"
        }
        
        response = client.post("/api/v1/users/", json=user_data, headers=admin_auth_headers)
        
        assert response.status_code == 201
        data = response.json()
        assert data["username"] == "newuser"
        assert data["role"] == "USER"
        assert data["state"] == "ACTIVE"
        assert "id" in data
        assert "password" not in data
    
    def test_create_user_duplicate_username(self, client: TestClient, admin_auth_headers: dict, test_user: User):
        """Test creating a user with duplicate username."""
        user_data = {
            "username": "testuser",  # Same as existing user
            "password": "newpassword123",
            "role": "USER"
        }
        
        response = client.post("/api/v1/users/", json=user_data, headers=admin_auth_headers)
        
        assert response.status_code == 400
        data = response.json()
        assert "detail" in data
        assert "Username already registered" in data["detail"]
    
    def test_create_user_unauthorized(self, client: TestClient):
        """Test creating a user without authentication."""
        user_data = {
            "username": "newuser",
            "password": "newpassword123",
            "role": "USER"
        }
        
        response = client.post("/api/v1/users/", json=user_data)
        
        assert response.status_code == 401
    
    def test_update_user_admin(self, client: TestClient, admin_auth_headers: dict, test_user: User):
        """Test updating a user with admin access."""
        update_data = {
            "username": "updateduser",
            "role": "SUPERVISOR"
        }
        
        response = client.put(f"/api/v1/users/{test_user.id}", json=update_data, headers=admin_auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["username"] == "updateduser"
        assert data["role"] == "SUPERVISOR"
        assert data["state"] == "INACTIVE"
        assert "password" not in data
    
    def test_update_user_own_profile(self, client: TestClient, auth_headers: dict, test_user: User):
        """Test updating own user profile."""
        update_data = {
            "username": "myupdatedusername"
        }
        
        response = client.put(f"/api/v1/users/{test_user.id}", json=update_data, headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["username"] == "myupdatedusername"
    
    def test_update_user_other_user_unauthorized(self, client: TestClient, auth_headers: dict, test_admin: User):
        """Test updating another user's profile without proper permissions."""
        update_data = {
            "username": "unauthorized_update"
        }
        
        response = client.put(f"/api/v1/users/{test_admin.id}", json=update_data, headers=auth_headers)
        
        assert response.status_code == 403
    
    def test_update_user_not_found(self, client: TestClient, admin_auth_headers: dict):
        """Test updating a non-existent user."""
        import uuid
        fake_id = str(uuid.uuid4())
        update_data = {
            "username": "updateduser"
        }
        
        response = client.put(f"/api/v1/users/{fake_id}", json=update_data, headers=admin_auth_headers)
        
        assert response.status_code == 404
    
    def test_delete_user_admin(self, client: TestClient, admin_auth_headers: dict, db: Session):
        """Test deleting a user with admin access."""
        # Create a user to delete
        user_data = {
            "username": "user_to_delete",
            "password": "password123",
            "role": "USER"
        }
        
        create_response = client.post("/api/v1/users/", json=user_data, headers=admin_auth_headers)
        assert create_response.status_code == 201
        user_id = create_response.json()["id"]
        
        # Delete the user
        response = client.delete(f"/api/v1/users/{user_id}", headers=admin_auth_headers)
        
        assert response.status_code == 204
    
    def test_delete_user_unauthorized(self, client: TestClient, auth_headers: dict, test_admin: User):
        """Test deleting a user without proper permissions."""
        response = client.delete(f"/api/v1/users/{test_admin.id}", headers=auth_headers)
        
        assert response.status_code == 403
    
    def test_delete_user_not_found(self, client: TestClient, admin_auth_headers: dict):
        """Test deleting a non-existent user."""
        import uuid
        fake_id = str(uuid.uuid4())
        
        response = client.delete(f"/api/v1/users/{fake_id}", headers=admin_auth_headers)
        
        assert response.status_code == 404
    
    def test_get_user_teams(self, client: TestClient, auth_headers: dict, test_user: User, test_team: Team, db: Session):
        """Test getting user's teams."""
        # Add user to team
        test_user.teams.append(test_team)
        db.commit()
        
        response = client.get(f"/api/v1/users/{test_user.id}/teams", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        assert any(team["id"] == str(test_team.id) for team in data)
    
    def test_add_user_to_team_admin(self, client: TestClient, admin_auth_headers: dict, test_user: User, test_team: Team):
        """Test adding a user to a team with admin access."""
        response = client.post(f"/api/v1/users/{test_user.id}/teams/{test_team.id}", headers=admin_auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "User added to team successfully" in data["message"]
    
    def test_remove_user_from_team_admin(self, client: TestClient, admin_auth_headers: dict, test_user: User, test_team: Team, db: Session):
        """Test removing a user from a team with admin access."""
        # First add user to team
        test_user.teams.append(test_team)
        db.commit()
        
        response = client.delete(f"/api/v1/users/{test_user.id}/teams/{test_team.id}", headers=admin_auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "User removed from team successfully" in data["message"]
