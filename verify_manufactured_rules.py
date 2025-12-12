
import sys
import os
from datetime import date
from unittest.mock import MagicMock, patch

# Add the project root to the python path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(current_dir)) # Adjust as needed to reach root
sys.path.append(project_root)

# Mocking the imports before they are loaded by the module
sys.modules['sqlalchemy.orm'] = MagicMock()
sys.modules['app.modules.automation.services.utils.team_selection_service'] = MagicMock()
sys.modules['app.modules.automation.services.utils.capacity_verification_service'] = MagicMock()
sys.modules['app.shared.core.enums'] = MagicMock()
# Mock ServiceConfig to return keywords for fabrication
mock_config = MagicMock()
mock_config.get_activity_keywords.return_value = ["MOLINO", "FABRICACION", "MEZCLA", "BOLSA", "PULVERIZACION"]
sys.modules['app.modules.automation.services.config'] = mock_config
from app.modules.automation.services.config import ServiceConfig

# Now import the class to test
from app.modules.automation.rules.Manufactured import ManufacturedRule

def test_manufactured_rules():
    print("Starting Verification of Manufactured Rules (Molino Update)...")
    
    rule = ManufacturedRule()
    db = MagicMock()
    
    # Mock Teams
    fab1 = MagicMock(); fab1.id = "fab1_id"; fab1.name = "FABRICADO 1"
    fab2 = MagicMock(); fab2.id = "fab2_id"; fab2.name = "FABRICADO 2"
    fab3 = MagicMock(); fab3.id = "fab3_id"; fab3.name = "FABRICADO 3"
    molino = MagicMock(); molino.id = "molino_id"; molino.name = "MOLINO"
    
    teams_data = {
        "teams_by_type": {
            "fabricado1": fab1, "fabricado2": fab2, "fabricado3": fab3, "molino": molino
        }
    }
    
    # 1. TEST FILTER ACTIVITIES
    print("\nTest 0: Filter Activities (M2-M5 should be preserved)")
    # M1 is packaging only, M2-M5 can be fabrication too per new rules
    activities_input = {
        "activities_by_code": {
            "CODE1": {
                "activities": [
                    {"type": "M1", "activity": "Empaque"}, # Should be filtered out
                    {"type": "M2", "activity": "Microlotes"}, # Should BE KEPT
                    {"type": "M3", "activity": "Bolsa"},      # Should BE KEPT
                    {"type": "M9", "activity": "Pulverizacion"}, # Should BE KEPT
                    {"type": "M4", "activity": "Semi"},       # Should BE KEPT
                    {"type": "M5", "activity": "Auto"}        # Should BE KEPT
                ]
            }
        }
    }
    filtered = rule.filter_activities(activities_input)
    # Check if CODE1 is in results
    if "CODE1" in filtered["fabrication_activities_by_code"]:
        acts = filtered["fabrication_activities_by_code"]["CODE1"]["fabrication_activities"]
        types = [a["type"] for a in acts]
        print(f"  Types kept: {types}")
        # Expect M2, M3, M4, M5, M9 to be present. M1 absent.
        # Before fix: M2, M3, M5 likely absent (in exclusion list).
        if "M3" in types and "M9" in types and "M5" in types:
             print("  PASS: Critical types preserved.")
        else:
             print("  FAIL: Critical types filtered out! (Expected before fix)")
    else:
        print("  FAIL: CODE1 not found in filtered results.")

    # 2. TEST TEAM SELECTION
    with patch('app.modules.automation.services.utils.team_selection_service.TeamSelectionService') as MockTeamService:
        MockTeamService.get_fabrication_teams.return_value = teams_data
        
        with patch('app.modules.automation.services.utils.capacity_verification_service.CapacityVerificationService') as MockCapacityService:
            MockCapacityService.check_team_capacity.return_value = {"is_at_limit": False, "is_over_limit": False, "total_minutes": 0}

            # Test M9 -> MOLINO
            print("\nTest 1: M9 (Pulverización/Molienda)")
            res = rule.get_most_suitable_team(db, {"code": "ANY", "quantity": 10}, "M9")
            print(f"  Result: {res['selected_team']['name'] if res['selected_team'] else 'None'}")
            if res['selected_team']['type'] == 'molino':
                print("  PASS")
            else:
                print("  FAIL (Expected MOLINO)")

            # Test M3 -> MOLINO
            print("\nTest 2: M3 (Bolsa)")
            res = rule.get_most_suitable_team(db, {"code": "ANY", "quantity": 10}, "M3")
            print(f"  Result: {res['selected_team']['name'] if res['selected_team'] else 'None'}")
            if res['selected_team']['type'] == 'molino':
                print("  PASS")
            else:
                print("  FAIL (Expected MOLINO)")

            # Test M2 -> FABRICADO 3 (As per previous logic 'Microlotes' or new Logic? Prompt said: M2: Absorbe microlotes de su familia (under MOLINO section??)
            # Wait, let's re-read the prompt VERY CAREFULLY.
            # "MOLINO: ... M2: Absorbe microlotes de su familia de productos."
            # So M2 should go to MOLINO now?
            # Previous prompt said for FABRICADO 3: "M2 (Microlotes/Manual): Gran contribuyente de volumen."
            # New prompt for MOLINO: "M2: Absorbe microlotes de su familia de productos."
            # This implies M2 could go to Molino OR Fabricado 3 depending on "familia".
            # Since we don't have family logic, and Molino has M2 listed under it in the new prompt, I should probably prioritize Molino or check if it fits Molino logic.
            # BUT, usually "Absorbs from family" implies specific cases.
            # If I put M2 -> MOLINO generally, does it break FAB 3?
            # Let's assume M2 -> MOLINO is the new overriding rule or shared.
            # I'll assign M2 to Molino for now based on the latest prompt section for PROCEED.
            print("\nTest 3: M2 (Microlotes)")
            res = rule.get_most_suitable_team(db, {"code": "ANY", "quantity": 10}, "M2")
            print(f"  Result: {res['selected_team']['name'] if res['selected_team'] else 'None'}")
            

if __name__ == "__main__":
    try:
        test_manufactured_rules()
        print("\nVerification Script Completed.")
    except Exception as e:
        print(f"\nVerification Script Failed: {e}")
        import traceback
        traceback.print_exc()
