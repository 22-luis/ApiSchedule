"""
Tests para el endpoint de programaciones disponibles por equipo
"""
import pytest
from datetime import date, timedelta
from uuid import uuid4
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.modules.programming.models.programming import Programming, ProgrammingStatus
from app.modules.organization.models.team import Team
from app.modules.organization.models.user import User, UserRole
from app.modules.organization.models.state import UserState


class TestAvailableProgrammingsForTeam:
    """Tests para el endpoint GET /programmings/team/{team_uuid}/available"""
    
    def test_get_available_programmings_existing(self, client: TestClient, db: Session, admin_user: User):
        """Test obtener programaciones disponibles cuando existen"""
        # Crear equipo
        team = Team(id=uuid4(), name="Equipo Test")
        db.add(team)
        db.commit()
        
        # Crear programaciones disponibles
        today = date.today()
        tomorrow = today + timedelta(days=1)
        
        programming1 = Programming(
            id=uuid4(),
            date=today,
            team_id=team.id,
            status=ProgrammingStatus.available
        )
        programming2 = Programming(
            id=uuid4(),
            date=tomorrow,
            team_id=team.id,
            status=ProgrammingStatus.available
        )
        
        db.add_all([programming1, programming2])
        db.commit()
        
        # Hacer request
        response = client.get(
            f"/programmings/team/{team.id}/available",
            headers={"Authorization": f"Bearer {admin_user.token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["team_id"] == str(team.id)
        assert data["team_name"] == team.name
        assert len(data["available_programmings"]) == 2
        
        # Verificar que las fechas están en orden
        dates = [p["date"] for p in data["available_programmings"]]
        assert dates == [today.isoformat(), tomorrow.isoformat()]
    
    def test_get_available_programmings_no_future(self, client: TestClient, db: Session, admin_user: User):
        """Test crear programación automáticamente cuando no hay programaciones futuras"""
        # Crear equipo
        team = Team(id=uuid4(), name="Equipo Test")
        db.add(team)
        db.commit()
        
        # Crear programación pasada
        yesterday = date.today() - timedelta(days=1)
        past_programming = Programming(
            id=uuid4(),
            date=yesterday,
            team_id=team.id,
            status=ProgrammingStatus.available
        )
        
        db.add(past_programming)
        db.commit()
        
        # Hacer request
        response = client.get(
            f"/programmings/team/{team.id}/available",
            headers={"Authorization": f"Bearer {admin_user.token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["team_id"] == str(team.id)
        assert data["team_name"] == team.name
        assert len(data["available_programmings"]) == 1
        
        # Verificar que se creó una programación para hoy
        new_date = data["available_programmings"][0]["date"]
        assert new_date == date.today().isoformat()
    
    def test_get_available_programmings_no_programmings(self, client: TestClient, db: Session, admin_user: User):
        """Test crear programación cuando no hay ninguna programación"""
        # Crear equipo
        team = Team(id=uuid4(), name="Equipo Test")
        db.add(team)
        db.commit()
        
        # Hacer request
        response = client.get(
            f"/programmings/team/{team.id}/available",
            headers={"Authorization": f"Bearer {admin_user.token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["team_id"] == str(team.id)
        assert data["team_name"] == team.name
        assert len(data["available_programmings"]) == 1
        
        # Verificar que se creó una programación para mañana
        tomorrow = date.today() + timedelta(days=1)
        new_date = data["available_programmings"][0]["date"]
        assert new_date == tomorrow.isoformat()
    
    def test_get_available_programmings_team_not_found(self, client: TestClient, admin_user: User):
        """Test error cuando el equipo no existe"""
        fake_team_id = uuid4()
        
        response = client.get(
            f"/programmings/team/{fake_team_id}/available",
            headers={"Authorization": f"Bearer {admin_user.token}"}
        )
        
        assert response.status_code == 404
        assert "Team not found" in response.json()["detail"]
    
    def test_get_available_programmings_unauthorized(self, client: TestClient, db: Session, regular_user: User):
        """Test error cuando el usuario no tiene permisos"""
        # Crear equipo
        team = Team(id=uuid4(), name="Equipo Test")
        db.add(team)
        db.commit()
        
        response = client.get(
            f"/programmings/team/{team.id}/available",
            headers={"Authorization": f"Bearer {regular_user.token}"}
        )
        
        assert response.status_code == 403
        assert "Not authorized" in response.json()["detail"]
    
    def test_get_available_programmings_only_available_status(self, client: TestClient, db: Session, admin_user: User):
        """Test que solo devuelve programaciones con estado available"""
        # Crear equipo
        team = Team(id=uuid4(), name="Equipo Test")
        db.add(team)
        db.commit()
        
        # Crear programaciones con diferentes estados
        today = date.today()
        
        available_programming = Programming(
            id=uuid4(),
            date=today,
            team_id=team.id,
            status=ProgrammingStatus.available
        )
        
        unavailable_programming = Programming(
            id=uuid4(),
            date=today + timedelta(days=1),
            team_id=team.id,
            status=ProgrammingStatus.unavailable
        )
        
        db.add_all([available_programming, unavailable_programming])
        db.commit()
        
        # Hacer request
        response = client.get(
            f"/programmings/team/{team.id}/available",
            headers={"Authorization": f"Bearer {admin_user.token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Solo debe devolver la programación disponible
        assert len(data["available_programmings"]) == 1
        assert data["available_programmings"][0]["date"] == today.isoformat()


@pytest.fixture
def admin_user(db: Session) -> User:
    """Fixture para crear un usuario administrador"""
    user = User(
        id=uuid4(),
        name="Admin User",
        email="admin@test.com",
        role=UserRole.admin,
        state=UserState.ACTIVE
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def regular_user(db: Session) -> User:
    """Fixture para crear un usuario regular"""
    user = User(
        id=uuid4(),
        name="Regular User",
        email="user@test.com",
        role=UserRole.user,
        state=UserState.ACTIVE
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user
