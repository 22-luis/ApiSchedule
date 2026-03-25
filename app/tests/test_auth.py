"""
Tests for authentication endpoints.
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.modules.organization.models.user import User
from app.modules.organization.models.role import UserRole
from app.shared.utils.security.security import hash_password

class TestAuth:
    """Test authentication endpoints."""
    
    def test_login_success(self, client: TestClient, db: Session, test_user: User):
        """Test successful login."""
        # Hash the password for the test user
        test_user.password = hash_password("testpassword123")
        db.commit()
        
        response = client.post("/api/v1/auth/login", data={
            "username": "testuser",
            "password": "testpassword123"
        })
        
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "token_type" in data
        assert data["token_type"] == "bearer"
        assert "user" in data
        assert data["user"]["username"] == "testuser"
        assert data["user"]["role"] == "USER"
    
    def test_login_invalid_credentials(self, client: TestClient, db: Session, test_user: User):
        """Test login with invalid credentials."""
        # Hash the password for the test user
        test_user.password = hash_password("testpassword123")
        db.commit()
        
        response = client.post("/api/v1/auth/login", data={
            "username": "testuser",
            "password": "wrongpassword"
        })
        
        assert response.status_code == 401
        data = response.json()
        assert "detail" in data
        assert "Incorrect username or password" in data["detail"]
    
    def test_login_nonexistent_user(self, client: TestClient):
        """Test login with non-existent user."""
        response = client.post("/api/v1/auth/login", data={
            "username": "nonexistent",
            "password": "password123"
        })
        
        assert response.status_code == 401
        data = response.json()
        assert "detail" in data
        assert "Incorrect username or password" in data["detail"]
    
    def test_login_missing_fields(self, client: TestClient):
        """Test login with missing fields."""
        response = client.post("/api/v1/auth/login", data={
            "username": "testuser"
            # Missing password
        })
        
        assert response.status_code == 422
    
    def test_register_user_success(self, client: TestClient, db: Session):
        """Test successful user registration."""
        user_data = {
            "username": "newuser",
            "password": "newpassword123",
            "role": "USER"
        }
        
        response = client.post("/api/v1/auth/register", json=user_data)
        
        assert response.status_code == 201
        data = response.json()
        assert data["username"] == "newuser"
        assert data["role"] == "USER"
        assert "id" in data
        assert "password" not in data  # Password should not be returned
    
    def test_register_user_duplicate_username(self, client: TestClient, db: Session, test_user: User):
        """Test user registration with duplicate username."""
        user_data = {
            "username": "testuser",  # Same as existing user
            "password": "newpassword123",
            "role": "USER"
        }
        
        response = client.post("/api/v1/auth/register", json=user_data)
        
        assert response.status_code == 400
        data = response.json()
        assert "detail" in data
        assert "Username already registered" in data["detail"]
    
    def test_register_user_invalid_role(self, client: TestClient):
        """Test user registration with invalid role."""
        user_data = {
            "username": "newuser",
            "password": "newpassword123",
            "role": "INVALID_ROLE"
        }
        
        response = client.post("/api/v1/auth/register", json=user_data)
        
        assert response.status_code == 422
    
    def test_get_current_user_success(self, client: TestClient, auth_headers: dict):
        """Test getting current user with valid token."""
        response = client.get("/api/v1/auth/me", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["username"] == "testuser"
        assert data["role"] == "USER"
        assert "id" in data
        assert "password" not in data
    
    def test_get_current_user_invalid_token(self, client: TestClient):
        """Test getting current user with invalid token."""
        response = client.get("/api/v1/auth/me", headers={
            "Authorization": "Bearer invalid_token"
        })
        
        assert response.status_code == 401
    
    def test_get_current_user_no_token(self, client: TestClient):
        """Test getting current user without token."""
        response = client.get("/api/v1/auth/me")
        
        assert response.status_code == 401
    
    def test_refresh_token_success(self, client: TestClient, auth_headers: dict):
        """Test token refresh."""
        response = client.post("/api/v1/auth/refresh", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "token_type" in data
        assert data["token_type"] == "bearer"
    
    def test_refresh_token_invalid_token(self, client: TestClient):
        """Test token refresh with invalid token."""
        response = client.post("/api/v1/auth/refresh", headers={
            "Authorization": "Bearer invalid_token"
        })
        
        assert response.status_code == 401
    
    def test_logout_success(self, client: TestClient, auth_headers: dict):
        """Test logout."""
        response = client.post("/api/v1/auth/logout", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "Successfully logged out" in data["message"]
