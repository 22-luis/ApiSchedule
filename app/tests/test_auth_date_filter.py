import pytest
from datetime import date, timedelta
from sqlalchemy.orm import Session
from fastapi.testclient import TestClient
from app.modules.organization.models.user import User
from app.modules.organization.models.team import Team, UserTeam
from app.shared.utils.security.security import hash_password

def test_active_team_ids_filtering(db: Session, client: TestClient, test_user_data: dict):
    """
    Verifies that the User's active_team_ids correctly filters teams based on 
    start_date and end_date relative to the current date.
    """
    # Setup: Create user with hashed password
    user_data = test_user_data.copy()
    user_data["password"] = hash_password("testpassword123")
    user = User(**user_data)
    db.add(user)
    db.flush() # Ensure user has an ID
    
    # Create teams
    team_active = Team(name="Active Team")
    team_future = Team(name="Future Team")
    team_past = Team(name="Past Team")
    team_no_end = Team(name="No End Team")
    db.add_all([team_active, team_future, team_past, team_no_end])
    db.commit()
    
    # Create associations
    today = date.today()
    
    # 1. Active: starts yesterday, ends tomorrow
    db.add(UserTeam(
        user_id=user.id, 
        team_id=team_active.id, 
        start_date=today - timedelta(days=1), 
        end_date=today + timedelta(days=1)
    ))
    
    # 2. Future: starts tomorrow
    db.add(UserTeam(
        user_id=user.id, 
        team_id=team_future.id, 
        start_date=today + timedelta(days=1)
    ))
    
    # 3. Past: ended yesterday
    db.add(UserTeam(
        user_id=user.id, 
        team_id=team_past.id, 
        start_date=today - timedelta(days=5), 
        end_date=today - timedelta(days=1)
    ))
    
    # 4. Active (no end date): started yesterday
    db.add(UserTeam(
        user_id=user.id, 
        team_id=team_no_end.id, 
        start_date=today - timedelta(days=1), 
        end_date=None
    ))
    
    db.commit()
    
    # Test model property logic directly
    active_ids = user.active_team_ids
    assert len(active_ids) == 2
    assert team_active.id in active_ids
    assert team_no_end.id in active_ids
    assert team_future.id not in active_ids
    assert team_past.id not in active_ids
    
    # Test through login API to ensure the response uses the filtered IDs
    response = client.post("/api/v1/auth/login", data={
        "username": user.username,
        "password": "testpassword123"
    })
    
    assert response.status_code == 200
    data = response.json()
    returned_team_ids = data["user"]["teamIds"]
    
    # Convert to string for comparison (UUIDs in JSON are strings)
    returned_team_ids_str = [str(tid) for tid in returned_team_ids]
    
    assert len(returned_team_ids) == 2
    assert str(team_active.id) in returned_team_ids_str
    assert str(team_no_end.id) in returned_team_ids_str
    assert str(team_future.id) not in returned_team_ids_str
    assert str(team_past.id) not in returned_team_ids_str

def test_team_ids_property_alias(db: Session, test_user: User, test_team: Team):
    """
    Verifies that the teamIds property acts as an alias for active_team_ids.
    """
    today = date.today()
    
    # Assign team as active
    db.add(UserTeam(
        user_id=test_user.id,
        team_id=test_team.id,
        start_date=today
    ))
    db.commit()
    
    assert test_team.id in test_user.active_team_ids
    assert test_team.id in test_user.teamIds
    assert test_user.teamIds == test_user.active_team_ids
