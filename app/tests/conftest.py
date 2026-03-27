"""
Pytest configuration and fixtures for ApiSchedule tests.
"""
import pytest
import asyncio
from typing import Generator, Dict, Any
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
import uuid
from datetime import datetime, date, timedelta

from app.main import app
from app.shared.db.database import Base
from app.shared.db.dependency import get_db
from app.modules.organization.models.user import User
from app.modules.organization.models.team import Team
from app.modules.programming.models.task import Task
from app.modules.orders.models.order import Order
from app.modules.programming.models.preparation import Preparation
from app.modules.codes.models.code import Code
from app.modules.programming.models.programming import Programming, ProgrammingTask
from app.modules.organization.models.role import UserRole
from app.shared.utils.security.jwt import create_access_token

# Test database configuration
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    """Override database dependency for testing."""
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

# Override the database dependency
app.dependency_overrides[get_db] = override_get_db

@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(scope="function")
def db() -> Generator[Session, None, None]:
    """Database session fixture."""
    # Create tables
    Base.metadata.create_all(bind=engine)
    
    # Create session
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        # Drop tables after test
        Base.metadata.drop_all(bind=engine)

@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    """Test client fixture."""
    with TestClient(app) as c:
        yield c

@pytest.fixture
def test_user_data() -> Dict[str, Any]:
    """Test user data fixture."""
    return {
        "username": "testuser",
        "password": "testpassword123",
        "role": UserRole.USER
    }

@pytest.fixture
def test_admin_data() -> Dict[str, Any]:
    """Test admin user data fixture."""
    return {
        "username": "admin",
        "password": "adminpassword123",
        "role": UserRole.ADMIN
    }

@pytest.fixture
def test_supervisor_data() -> Dict[str, Any]:
    """Test supervisor user data fixture."""
    return {
        "username": "supervisor",
        "password": "supervisorpassword123",
        "role": UserRole.SUPERVISOR
    }

@pytest.fixture
def test_planner_data() -> Dict[str, Any]:
    """Test planner user data fixture."""
    return {
        "username": "planner",
        "password": "plannerpassword123",
        "role": UserRole.PLANNER
    }

@pytest.fixture
def test_user(db: Session, test_user_data: Dict[str, Any]) -> User:
    """Create a test user."""
    user = User(**test_user_data)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

@pytest.fixture
def test_admin(db: Session, test_admin_data: Dict[str, Any]) -> User:
    """Create a test admin user."""
    user = User(**test_admin_data)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

@pytest.fixture
def test_supervisor(db: Session, test_supervisor_data: Dict[str, Any]) -> User:
    """Create a test supervisor user."""
    user = User(**test_supervisor_data)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

@pytest.fixture
def test_planner(db: Session, test_planner_data: Dict[str, Any]) -> User:
    """Create a test planner user."""
    user = User(**test_planner_data)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

@pytest.fixture
def test_team_data() -> Dict[str, Any]:
    """Test team data fixture."""
    return {
        "name": "Test Team",
        "supervisorId": None  # Will be set in tests
    }

@pytest.fixture
def test_team(db: Session, test_team_data: Dict[str, Any], test_supervisor: User) -> Team:
    """Create a test team."""
    team_data = test_team_data.copy()
    team_data["supervisorId"] = test_supervisor.id
    team = Team(**team_data)
    db.add(team)
    db.commit()
    db.refresh(team)
    return team

@pytest.fixture
def test_code_data() -> Dict[str, Any]:
    """Test code data fixture."""
    return {
        "code": "TEST001",
        "description": "Test Code Description",
        "unit": "kg",
        "type": "production",
        "activity": "manufacturing",
        "quantity": "100",
        "time": 120.0,
        "people": 5,
        "performance": 0.85,
        "material": "Test Material",
        "presentation": "Test Presentation",
        "fabricationCode": "FAB001",
        "usefulLife": "30 days"
    }

@pytest.fixture
def test_code(db: Session, test_code_data: Dict[str, Any]) -> Code:
    """Create a test code."""
    code = Code(**test_code_data)
    db.add(code)
    db.commit()
    db.refresh(code)
    return code

@pytest.fixture
def test_preparation_data() -> Dict[str, Any]:
    """Test preparation data fixture."""
    return {
        "description": "Test Preparation",
        "minutes": 30
    }

@pytest.fixture
def test_preparation(db: Session, test_preparation_data: Dict[str, Any]) -> Preparation:
    """Create a test preparation."""
    prep = Preparation(**test_preparation_data)
    db.add(prep)
    db.commit()
    db.refresh(prep)
    return prep

@pytest.fixture
def test_order_data() -> Dict[str, Any]:
    """Test order data fixture."""
    return {
        "lote": 12345,
        "description": "Test Order",
        "quantity": 100,
        "dueDate": date.today() + timedelta(days=7),
        "status": "PENDING",
        "code": "TEST001",
        "bin": 1
    }

@pytest.fixture
def test_order(db: Session, test_order_data: Dict[str, Any]) -> Order:
    """Create a test order."""
    order = Order(**test_order_data)
    db.add(order)
    db.commit()
    db.refresh(order)
    return order

@pytest.fixture
def test_programming_data() -> Dict[str, Any]:
    """Test programming data fixture."""
    return {
        "date": date.today(),
        "team_id": None  # Will be set in tests
    }

@pytest.fixture
def test_programming(db: Session, test_programming_data: Dict[str, Any], test_team: Team) -> Programming:
    """Create a test programming."""
    prog_data = test_programming_data.copy()
    prog_data["team_id"] = test_team.id
    programming = Programming(**prog_data)
    db.add(programming)
    db.commit()
    db.refresh(programming)
    return programming

@pytest.fixture
def test_task_data() -> Dict[str, Any]:
    """Test task data fixture."""
    return {
        "total_time": 120,
        "minutes": 120,
        "start_time": datetime.now(),
        "end_time": datetime.now() + timedelta(hours=2),
        "teamIds": [],  # Will be set in tests
        "programming_id": None,  # Will be set in tests
        "code_id": None,  # Will be set in tests
        "lote": "TEST123",
        "quantity": 50,
        "specification": "Test specification",
        "preparation_id": None,  # Will be set in tests
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

@pytest.fixture
def test_task(db: Session, test_task_data: Dict[str, Any], test_code: Code, test_programming: Programming) -> Task:
    """Create a test task."""
    task_data = test_task_data.copy()
    task_data["code_id"] = test_code.id
    # Remove fields not in model
    if "teamIds" in task_data:
        del task_data["teamIds"]
    if "programming_id" in task_data:
        del task_data["programming_id"]
    if "total_time" in task_data:
        del task_data["total_time"]
    
    task = Task(**task_data)
    db.add(task)
    db.commit()
    db.refresh(task)
    return task

@pytest.fixture
def auth_headers(test_user: User) -> Dict[str, str]:
    """Create authentication headers for a test user."""
    token = create_access_token(data={"sub": str(test_user.id)})
    return {"Authorization": f"Bearer {token}"}

@pytest.fixture
def admin_auth_headers(test_admin: User) -> Dict[str, str]:
    """Create authentication headers for an admin user."""
    token = create_access_token(data={"sub": str(test_admin.id)})
    return {"Authorization": f"Bearer {token}"}

@pytest.fixture
def supervisor_auth_headers(test_supervisor: User) -> Dict[str, str]:
    """Create authentication headers for a supervisor user."""
    token = create_access_token(data={"sub": str(test_supervisor.id)})
    return {"Authorization": f"Bearer {token}"}

@pytest.fixture
def planner_auth_headers(test_planner: User) -> Dict[str, str]:
    """Create authentication headers for a planner user."""
    token = create_access_token(data={"sub": str(test_planner.id)})
    return {"Authorization": f"Bearer {token}"}
