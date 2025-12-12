
import sys
import os
from unittest.mock import MagicMock, patch

# Add the project root to the python path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(current_dir)) # Adjust as needed to reach root
sys.path.append(project_root)

# Mocking the imports before they are loaded by the module
sys.modules['sqlalchemy.orm'] = MagicMock()
sys.modules['app.modules.automation.services.utils.team_selection_service'] = MagicMock()
# Mock generic enums and config if needed
sys.modules['app.shared.core.enums'] = MagicMock()
mock_config = MagicMock()
mock_config.get_activity_keywords.return_value = ["EMPAQUE", "MAQUINA"]
sys.modules['app.modules.automation.services.config'] = mock_config

# Now import the class to test
from app.modules.automation.rules.packaging import PackagingRule

def test_packaging_rules():
    print("Starting Verification of Packaging Rules...")
    
    rule = PackagingRule()
    db = MagicMock()
    
    # Mock Teams
    emp1 = MagicMock(); emp1.id = "emp1_id"; emp1.name = "EMPAQUE 1"
    emp2 = MagicMock(); emp2.id = "emp2_id"; emp2.name = "EMPAQUE 2"
    emp3 = MagicMock(); emp3.id = "emp3_id"; emp3.name = "EMPAQUE 3"
    maq1 = MagicMock(); maq1.id = "maq1_id"; maq1.name = "MAQUINA 1"
    maq2 = MagicMock(); maq2.id = "maq2_id"; maq2.name = "MAQUINA 2"
    molino = MagicMock(); molino.id = "mol_id"; molino.name = "MOLINO"
    fab3 = MagicMock(); fab3.id = "fab3_id"; fab3.name = "FABRICADO 3"
    
    packaging_teams = {
        "teams_by_type": {
            "empaque1": emp1, "empaque2": emp2, "empaque3": emp3,
            "maquina1": maq1, "maquina2": maq2
        }
    }
    fabrication_teams = {
        "teams_by_type": {
            "molino": molino, "fabricado3": fab3 
        }
    }
    
    with patch('app.modules.automation.services.utils.team_selection_service.TeamSelectionService') as MockTeamService:
        MockTeamService.get_packaging_teams.return_value = packaging_teams
        MockTeamService.get_fabrication_teams.return_value = fabrication_teams
        MockTeamService.get_weighing_team.return_value = {"success": True}

        # Test 1: M2 -> EMPAQUE 1 (General Leader)
        print("\nTest 1: M2 (Microlotes) - General")
        res = rule.get_most_suitable_team(db, {"code": "GEN123", "quantity": 10}, "M2")
        print(f"  Result: {res['selected_team']['name'] if res.get('selected_team') else 'None'}")
        
        # Test 2: M2 AX... -> EMPAQUE 3 (Specialist)
        print("\nTest 2: M2 (AX Series) -> EMPAQUE 3")
        res = rule.get_most_suitable_team(db, {"code": "AX100", "quantity": 10}, "M2")
        print(f"  Result: {res['selected_team']['name'] if res.get('selected_team') else 'None'}")

        # Test 3: M4 -> EMPAQUE 2 (Leader)
        print("\nTest 3: M4 (Semi Auto) -> EMPAQUE 2")
        res = rule.get_most_suitable_team(db, {"code": "ANY", "quantity": 100}, "M4")
        print(f"  Result: {res['selected_team']['name'] if res.get('selected_team') else 'None'}")
        
        # Test 4: M5 -> MAQUINA 2 (Leader)
        print("\nTest 4: M5 (Auto) -> MAQUINA 2")
        res = rule.get_most_suitable_team(db, {"code": "F1852", "quantity": 1000}, "M5")
        # Code F1852 is specific specialist for Maquina 2, but Maquina 2 is also Leader
        print(f"  Result: {res['selected_team']['name'] if res.get('selected_team') else 'None'}")

        # Test 5: M5 -> MAQUINA 1 (General/Overflow)
        print("\nTest 5: M5 (Auto General) -> MAQUINA 1/2 check")
        # Prompt says Maquina 2 is Leader ("Líder Absoluto"), Maquina 1 is overflow.
        # So "General" M5 should go to Maquina 2? 
        # "MAQUINA 2 ... Es la asignación primaria para el grueso de M5."
        # "MAQUINA 1 ... Desborde principal para M5".
        res = rule.get_most_suitable_team(db, {"code": "OTHER", "quantity": 1000}, "M5")
        print(f"  Result: {res['selected_team']['name'] if res.get('selected_team') else 'None'}")

        # Test 6: M15 -> EMPAQUE 3 (Small overflow/Support)
        print("\nTest 6: M15 -> EMPAQUE 3")
        res = rule.get_most_suitable_team(db, {"code": "ANY", "quantity": 5}, "M15") # M15 logic wasn't explicit in "Packaging" section other than "Soporte clave para M2 y Lotes M15" for Empaque 3.
        print(f"  Result: {res['selected_team']['name'] if res.get('selected_team') else 'None'}")

if __name__ == "__main__":
    try:
        test_packaging_rules()
        print("\nVerification Script Completed.")
    except Exception as e:
        print(f"\nVerification Script Failed: {e}")
        import traceback
        traceback.print_exc()
