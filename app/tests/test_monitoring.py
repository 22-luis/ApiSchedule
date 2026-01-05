
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_health_check():
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "uptime_seconds" in data
    assert "app_info" in data
    assert data["app_info"]["name"] == "ApiSchedule"

def test_detailed_health_check():
    response = client.get("/api/v1/health/detailed")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ["healthy", "warning", "unhealthy", "error"]
    assert "uptime_seconds" in data
    assert "checks" in data
    assert "database" in data["checks"]
    assert "app_info" in data
