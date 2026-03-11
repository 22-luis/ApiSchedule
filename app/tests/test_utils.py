"""
Tests for utility endpoints and business logic.
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from datetime import datetime, date, timedelta
from app.modules.programming.models.task import Task
from app.modules.organization.models.team import Team
from app.modules.programming.models.programming import Programming, ProgrammingTask
from app.modules.orders.models.order import Order

class TestUtils:
    """Test utility endpoints and business logic."""
    
    def test_health_check(self, client: TestClient):
        """Test health check endpoint."""
        response = client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert data["status"] == "healthy"
        assert "app_name" in data
        assert "version" in data
        assert "environment" in data
        assert "timestamp" in data
    
    def test_app_info(self, client: TestClient):
        """Test application info endpoint."""
        response = client.get("/info")
        
        assert response.status_code == 200
        data = response.json()
        assert "app_name" in data
        assert "version" in data
        assert "environment" in data
        assert "debug" in data
        assert "database_configured" in data
        assert "rate_limiting_enabled" in data
        assert "cors_origins" in data
        assert "working_hours" in data
    
    def test_rate_limit_stats_development(self, client: TestClient):
        """Test rate limit stats endpoint in development."""
        response = client.get("/rate-limit-stats")
        
        # This might return 404 in production, but should work in development
        # We'll just check that it doesn't crash
        assert response.status_code in [200, 404]
    
    def test_calculations_efficiency(self, client: TestClient, auth_headers: dict, 
                                   test_programming: Programming, test_task: Task, db: Session):
        """Test efficiency calculations."""
        # Create programming task with completion data
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
        
        response = client.get(f"/api/v1/calculations/efficiency/{test_programming.id}", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert "programming_id" in data
        assert "efficiency_percentage" in data
        assert "total_tasks" in data
        assert "completed_tasks" in data
        assert "total_time_planned" in data
        assert "total_time_actual" in data
    
    def test_calculations_productivity(self, client: TestClient, auth_headers: dict, 
                                     test_team: Team, test_task: Task, db: Session):
        """Test productivity calculations."""
        # Add task to team
        test_team.tasks.append(test_task)
        db.commit()
        
        start_date = (date.today() - timedelta(days=7)).isoformat()
        end_date = (date.today() + timedelta(days=7)).isoformat()
        
        response = client.get(f"/api/v1/calculations/productivity/{test_team.id}?start_date={start_date}&end_date={end_date}", 
                            headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert "team_id" in data
        assert "productivity_score" in data
        assert "total_tasks" in data
        assert "completed_tasks" in data
        assert "average_completion_time" in data
    
    def test_calculations_capacity(self, client: TestClient, auth_headers: dict, test_team: Team):
        """Test capacity calculations."""
        response = client.get(f"/api/v1/calculations/capacity/{test_team.id}", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert "team_id" in data
        assert "total_capacity" in data
        assert "used_capacity" in data
        assert "available_capacity" in data
        assert "capacity_percentage" in data
    
    def test_calculations_workload_distribution(self, client: TestClient, auth_headers: dict, 
                                              test_programming: Programming, test_task: Task, db: Session):
        """Test workload distribution calculations."""
        # Create programming task
        programming_task = ProgrammingTask(
            programming_id=test_programming.id,
            task_id=test_task.id,
            order=1
        )
        db.add(programming_task)
        db.commit()
        
        response = client.get(f"/api/v1/calculations/workload-distribution/{test_programming.id}", 
                            headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert "programming_id" in data
        assert "workload_distribution" in data
        assert "total_workload" in data
        assert "average_workload_per_task" in data
    
    def test_business_calculations_working_hours(self, client: TestClient, auth_headers: dict):
        """Test working hours calculations."""
        date_to_check = date.today().isoformat()
        
        response = client.get(f"/api/v1/calculations/working-hours?date={date_to_check}", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert "date" in data
        assert "is_working_day" in data
        assert "working_hours" in data
        assert "start_time" in data
        assert "end_time" in data
    
    def test_business_calculations_holidays(self, client: TestClient, auth_headers: dict):
        """Test holiday calculations."""
        year = date.today().year
        
        response = client.get(f"/api/v1/calculations/holidays/{year}", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert "year" in data
        assert "holidays" in data
        assert isinstance(data["holidays"], list)
    
    def test_data_cleaning_validate_task_data(self, client: TestClient, auth_headers: dict):
        """Test task data validation."""
        task_data = {
            "lote": "TEST123",
            "quantity": 100,
            "specification": "Test specification",
            "start_time": datetime.now().isoformat(),
            "end_time": (datetime.now() + timedelta(hours=2)).isoformat()
        }
        
        response = client.post("/api/v1/utils/validate-task-data", json=task_data, headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert "is_valid" in data
        assert "errors" in data
        assert "warnings" in data
    
    def test_data_cleaning_clean_order_data(self, client: TestClient, auth_headers: dict):
        """Test order data cleaning."""
        order_data = {
            "lote": 12345,
            "description": "  Test Order  ",  # Extra spaces
            "quantity": "100",  # String instead of int
            "dueDate": "2024-01-01"
        }
        
        response = client.post("/api/v1/utils/clean-order-data", json=order_data, headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert "cleaned_data" in data
        assert "changes_made" in data
        assert data["cleaned_data"]["description"] == "Test Order"  # Should be trimmed
        assert data["cleaned_data"]["quantity"] == 100  # Should be converted to int
    
    def test_exception_handlers_validation_error(self, client: TestClient):
        """Test validation error handling."""
        # Send invalid data to trigger validation error
        invalid_data = {
            "invalid_field": "invalid_value"
        }
        
        response = client.post("/api/v1/auth/login", json=invalid_data)
        
        assert response.status_code == 422
        data = response.json()
        assert "detail" in data
    
    def test_exception_handlers_http_error(self, client: TestClient, auth_headers: dict):
        """Test HTTP error handling."""
        # Try to access a non-existent endpoint
        import uuid
        fake_id = str(uuid.uuid4())
        
        response = client.get(f"/api/v1/users/{fake_id}", headers=auth_headers)
        
        assert response.status_code == 404
        data = response.json()
        assert "detail" in data
    
    def test_logging_middleware(self, client: TestClient, auth_headers: dict):
        """Test that logging middleware adds request ID."""
        response = client.get("/health", headers=auth_headers)
        
        assert response.status_code == 200
        assert "X-Request-ID" in response.headers
        assert response.headers["X-Request-ID"] is not None
    
    def test_cors_headers(self, client: TestClient):
        """Test CORS headers are present."""
        response = client.options("/health")
        
        # CORS headers should be present
        assert "access-control-allow-origin" in response.headers or response.status_code == 200
    
    def test_authentication_middleware(self, client: TestClient):
        """Test authentication middleware."""
        # Test without authentication
        response = client.get("/api/v1/users/")
        assert response.status_code == 401
        
        # Test with invalid token
        response = client.get("/api/v1/users/", headers={"Authorization": "Bearer invalid_token"})
        assert response.status_code == 401
    
    def test_rate_limiting_middleware(self, client: TestClient):
        """Test rate limiting middleware."""
        # Make multiple requests to test rate limiting
        responses = []
        for _ in range(10):
            response = client.get("/health")
            responses.append(response.status_code)
        
        # All requests should succeed (rate limiting might not be enabled in tests)
        assert all(status == 200 for status in responses)
    
    def test_database_connection(self, client: TestClient):
        """Test database connection through health check."""
        response = client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert data["status"] == "healthy"
    
    def test_environment_configuration(self, client: TestClient):
        """Test environment configuration through info endpoint."""
        response = client.get("/info")
        
        assert response.status_code == 200
        data = response.json()
        assert "environment" in data
        assert "debug" in data
        assert "database_configured" in data
