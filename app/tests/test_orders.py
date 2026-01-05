"""
Tests for order management endpoints.
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from datetime import date, timedelta
from app.modules.programming.models.order import Order

class TestOrders:
    """Test order management endpoints."""
    
    def test_get_orders_success(self, client: TestClient, auth_headers: dict, test_order: Order):
        """Test getting all orders."""
        response = client.get("/api/v1/orders/", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1  # At least the test order
        
        # Check order structure
        for order in data:
            assert "lote" in order
            assert "description" in order
            assert "quantity" in order
            assert "status" in order
            assert "dueDate" in order
    
    def test_get_orders_unauthorized(self, client: TestClient):
        """Test getting orders without authentication."""
        response = client.get("/api/v1/orders/")
        
        assert response.status_code == 401
    
    def test_get_order_by_lote_success(self, client: TestClient, auth_headers: dict, test_order: Order):
        """Test getting a specific order by lote."""
        response = client.get(f"/api/v1/orders/{test_order.lote}", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["lote"] == test_order.lote
        assert data["description"] == test_order.description
        assert data["quantity"] == test_order.quantity
        assert data["status"] == test_order.status.value
    
    def test_get_order_by_lote_not_found(self, client: TestClient, auth_headers: dict):
        """Test getting a non-existent order."""
        fake_lote = 99999
        response = client.get(f"/api/v1/orders/{fake_lote}", headers=auth_headers)
        
        assert response.status_code == 404
    
    def test_create_order_success(self, client: TestClient, admin_auth_headers: dict):
        """Test creating a new order."""
        order_data = {
            "lote": 54321,
            "description": "New Test Order",
            "quantity": 150,
            "dueDate": (date.today() + timedelta(days=14)).isoformat(),
            "status": "PENDING",
            "code": "NEW001",
            "bin": 2
        }
        
        response = client.post("/api/v1/orders/", json=order_data, headers=admin_auth_headers)
        
        assert response.status_code == 201
        data = response.json()
        assert data["lote"] == 54321
        assert data["description"] == "New Test Order"
        assert data["quantity"] == 150
        assert data["status"] == "PENDING"
    
    def test_create_order_unauthorized(self, client: TestClient):
        """Test creating an order without authentication."""
        order_data = {
            "lote": 54321,
            "description": "Unauthorized Order",
            "quantity": 150,
            "dueDate": date.today().isoformat(),
            "status": "PENDING"
        }
        
        response = client.post("/api/v1/orders/", json=order_data)
        
        assert response.status_code == 401
    
    def test_create_order_duplicate_lote(self, client: TestClient, admin_auth_headers: dict, test_order: Order):
        """Test creating an order with duplicate lote."""
        order_data = {
            "lote": test_order.lote,  # Same as existing order
            "description": "Duplicate Order",
            "quantity": 150,
            "dueDate": date.today().isoformat(),
            "status": "PENDING"
        }
        
        response = client.post("/api/v1/orders/", json=order_data, headers=admin_auth_headers)
        
        assert response.status_code == 400
        data = response.json()
        assert "detail" in data
        assert "Order with this lote already exists" in data["detail"]
    
    def test_update_order_success(self, client: TestClient, admin_auth_headers: dict, test_order: Order):
        """Test updating an order."""
        update_data = {
            "description": "Updated Order Description",
            "quantity": 200,
            "status": "IN_PROGRESS"
        }
        
        response = client.put(f"/api/v1/orders/{test_order.lote}", json=update_data, headers=admin_auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["description"] == "Updated Order Description"
        assert data["quantity"] == 200
        assert data["status"] == "IN_PROGRESS"
    
    def test_update_order_unauthorized(self, client: TestClient, test_order: Order):
        """Test updating an order without proper permissions."""
        update_data = {
            "description": "Unauthorized Update"
        }
        
        response = client.put(f"/api/v1/orders/{test_order.lote}", json=update_data)
        
        assert response.status_code == 401
    
    def test_update_order_not_found(self, client: TestClient, admin_auth_headers: dict):
        """Test updating a non-existent order."""
        fake_lote = 99999
        update_data = {
            "description": "Updated Description"
        }
        
        response = client.put(f"/api/v1/orders/{fake_lote}", json=update_data, headers=admin_auth_headers)
        
        assert response.status_code == 404
    
    def test_delete_order_success(self, client: TestClient, admin_auth_headers: dict, db: Session):
        """Test deleting an order."""
        # Create an order to delete
        order = Order(
            lote=98765,
            description="Order to Delete",
            quantity=100,
            dueDate=date.today() + timedelta(days=7),
            status="PENDING"
        )
        db.add(order)
        db.commit()
        db.refresh(order)
        
        # Delete the order
        response = client.delete(f"/api/v1/orders/{order.lote}", headers=admin_auth_headers)
        
        assert response.status_code == 204
    
    def test_delete_order_unauthorized(self, client: TestClient, test_order: Order):
        """Test deleting an order without proper permissions."""
        response = client.delete(f"/api/v1/orders/{test_order.lote}")
        
        assert response.status_code == 401
    
    def test_delete_order_not_found(self, client: TestClient, admin_auth_headers: dict):
        """Test deleting a non-existent order."""
        fake_lote = 99999
        
        response = client.delete(f"/api/v1/orders/{fake_lote}", headers=admin_auth_headers)
        
        assert response.status_code == 404
    
    def test_get_orders_by_status(self, client: TestClient, auth_headers: dict, test_order: Order):
        """Test getting orders by status."""
        response = client.get(f"/api/v1/orders/status/{test_order.status.value}", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        assert all(order["status"] == test_order.status.value for order in data)
    
    def test_get_orders_by_date_range(self, client: TestClient, auth_headers: dict, test_order: Order):
        """Test getting orders by date range."""
        start_date = (date.today() - timedelta(days=30)).isoformat()
        end_date = (date.today() + timedelta(days=30)).isoformat()
        
        response = client.get(f"/api/v1/orders/date-range?start_date={start_date}&end_date={end_date}", 
                             headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        assert any(order["lote"] == test_order.lote for order in data)
    
    def test_get_orders_by_code(self, client: TestClient, auth_headers: dict, test_order: Order):
        """Test getting orders by code."""
        response = client.get(f"/api/v1/orders/code/{test_order.code}", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        assert all(order["code"] == test_order.code for order in data)
    
    def test_update_order_status_success(self, client: TestClient, admin_auth_headers: dict, test_order: Order):
        """Test updating order status."""
        status_data = {
            "status": "COMPLETED"
        }
        
        response = client.patch(f"/api/v1/orders/{test_order.lote}/status", 
                              json=status_data, headers=admin_auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "COMPLETED"
    
    def test_update_order_status_invalid(self, client: TestClient, admin_auth_headers: dict, test_order: Order):
        """Test updating order status with invalid status."""
        status_data = {
            "status": "INVALID_STATUS"
        }
        
        response = client.patch(f"/api/v1/orders/{test_order.lote}/status", 
                              json=status_data, headers=admin_auth_headers)
        
        assert response.status_code == 422
    
    def test_get_orders_summary(self, client: TestClient, auth_headers: dict, test_order: Order):
        """Test getting orders summary."""
        response = client.get("/api/v1/orders/summary", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert "total_orders" in data
        assert "orders_by_status" in data
        assert "orders_by_date" in data
        assert isinstance(data["total_orders"], int)
        assert isinstance(data["orders_by_status"], dict)
        assert isinstance(data["orders_by_date"], list)
    
    def test_get_overdue_orders(self, client: TestClient, auth_headers: dict, db: Session):
        """Test getting overdue orders."""
        # Create an overdue order
        overdue_order = Order(
            lote=11111,
            description="Overdue Order",
            quantity=50,
            dueDate=date.today() - timedelta(days=5),  # Overdue
            status="PENDING"
        )
        db.add(overdue_order)
        db.commit()
        
        response = client.get("/api/v1/orders/overdue", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        assert any(order["lote"] == 11111 for order in data)
    
    def test_get_orders_by_bin(self, client: TestClient, auth_headers: dict, test_order: Order):
        """Test getting orders by bin."""
        response = client.get(f"/api/v1/orders/bin/{test_order.bin}", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        assert all(order["bin"] == test_order.bin for order in data)
