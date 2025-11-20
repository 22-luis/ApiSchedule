import sys
import os
from datetime import date, datetime
from unittest.mock import MagicMock, patch

# Add the project root to the python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.utils.business.programming_availability import get_programming_availability, TEAM_RULES
from app.models.programming import Programming, ProgrammingTask
from app.models.team import Team

def test_get_programming_availability():
    print("Testing get_programming_availability...")
    
    # Mock DB session
    db = MagicMock()
    
    # Mock Programming
    programming_id = "prog-123"
    programming = MagicMock(spec=Programming)
    programming.id = programming_id
    programming.team_id = "team-123"
    programming.date = date.today()
    
    # Mock Team
    team = MagicMock(spec=Team)
    team.id = "team-123"
    team.name = "Molino" # Has standard duration
    
    # Mock DB queries
    # First query is for Programming
    # Second query is for Team
    # Third query is for ProgrammingTasks
    
    def side_effect_query(model):
        query_mock = MagicMock()
        if model == Programming:
            query_mock.filter.return_value.first.return_value = programming
        elif model == Team:
            query_mock.filter.return_value.first.return_value = team
        elif model == ProgrammingTask:
            # Return empty list of tasks for simplicity first
            query_mock.filter.return_value.all.return_value = []
        return query_mock
        
    db.query.side_effect = side_effect_query
    
    # Test Case 1: Empty programming, small task -> Should be available
    print("  Case 1: Empty programming, small task")
    with patch('app.services.utils.programming_utils.ProgrammingUtils.calculate_current_programming_time', return_value=0):
        result = get_programming_availability(db, programming_id, 60)
        assert result["available"] == True
        assert result["current_end_minutes"] == 0
        assert result["final_minutes"] == 60
        print("    PASS")

    # Test Case 2: Full programming -> Should be unavailable
    print("  Case 2: Full programming")
    max_duration = TEAM_RULES["Molino"]["duration"]
    # Mock calculate_current_programming_time to return max_duration
    with patch('app.services.utils.programming_utils.ProgrammingUtils.calculate_current_programming_time', return_value=max_duration + 5):
        result = get_programming_availability(db, programming_id, 60)
        assert result["available"] == False
        assert result["current_end_minutes"] == max_duration + 5
        print("    PASS")

    print("All tests passed!")

if __name__ == "__main__":
    test_get_programming_availability()
