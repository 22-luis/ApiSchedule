from datetime import date, time
from unittest.mock import MagicMock
from app.shared.utils.business.programming_availability import get_cutoff_time_for_team

def test_cutoff_times():
    # Mock teams
    pesado_team = MagicMock()
    pesado_team.name = "Pesado Principal"
    
    other_team = MagicMock()
    other_team.name = "Fabricado 1"
    
    # Test Monday (Weekday 0)
    monday = date(2023, 11, 20) # A Monday
    assert get_cutoff_time_for_team(pesado_team, monday) == time(17, 40), "Pesado on Monday should be 17:40"
    assert get_cutoff_time_for_team(other_team, monday) == time(14, 40), "Other on Monday should be 14:40"
    
    # Test Friday (Weekday 4)
    friday = date(2023, 11, 24) # A Friday
    assert get_cutoff_time_for_team(pesado_team, friday) == time(17, 40), "Pesado on Friday should be 17:40"
    assert get_cutoff_time_for_team(other_team, friday) == time(14, 40), "Other on Friday should be 14:40"
    
    # Test Saturday (Weekday 5)
    saturday = date(2023, 11, 25) # A Saturday
    assert get_cutoff_time_for_team(pesado_team, saturday) == time(11, 10), "Pesado on Saturday should be 11:10"
    assert get_cutoff_time_for_team(other_team, saturday) == time(11, 10), "Other on Saturday should be 11:10"
    
    # Test Sunday (Weekday 6) - Should default to weekday logic as no specific rule for Sunday was requested, 
    # but let's verify it behaves as "not Saturday" for now based on implementation
    sunday = date(2023, 11, 26) # A Sunday
    assert get_cutoff_time_for_team(pesado_team, sunday) == time(17, 40), "Pesado on Sunday should be 17:40 (default)"
    assert get_cutoff_time_for_team(other_team, sunday) == time(14, 40), "Other on Sunday should be 14:40 (default)"

    # Test without date (backward compatibility)
    assert get_cutoff_time_for_team(pesado_team) == time(17, 40), "Pesado without date should be 17:40"
    assert get_cutoff_time_for_team(other_team) == time(14, 40), "Other without date should be 14:40"

if __name__ == "__main__":
    try:
        test_cutoff_times()
        print("All tests passed!")
    except AssertionError as e:
        print(f"Test failed: {e}")
    except Exception as e:
        print(f"An error occurred: {e}")
