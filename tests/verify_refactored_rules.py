
import sys
import os
from unittest.mock import MagicMock, patch

# Add the project root to the python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.modules.automation.rules.Manufactured import ManufacturedRule
from app.modules.automation.rules.packaging import PackagingRule
from app.modules.automation.rules.weighning import WeighingRule

# Mock Team objects
# Note: 'name' in MagicMock constructor sets the name of the mock, not the attribute .name
# So we must set the attribute explicitly or use a different way.
fab1 = MagicMock(id='fab1_id')
fab1.name = 'Fabricado 1'
fab2 = MagicMock(id='fab2_id')
fab2.name = 'Fabricado 2'
fab3 = MagicMock(id='fab3_id')
fab3.name = 'Fabricado 3'

maq1 = MagicMock(id='maq1_id')
maq1.name = 'Maquina 1'
maq2 = MagicMock(id='maq2_id')
maq2.name = 'Maquina 2'
molino = MagicMock(id='mol_id')
molino.name = 'Molino'

emp1 = MagicMock(id='emp1_id')
emp1.name = 'Empaque 1'
emp2 = MagicMock(id='emp2_id')
emp2.name = 'Empaque 2'
emp3 = MagicMock(id='emp3_id')
emp3.name = 'Empaque 3'
emp4 = MagicMock(id='emp4_id')
emp4.name = 'Empaque 4'

pesado = MagicMock(id='pesado_id')
pesado.name = 'Equipo de Pesado'

# Mock Teams Data
mock_fab_teams = {
    "teams_by_type": {
        "fabricado1": fab1, "fabricado2": fab2, "fabricado3": fab3,
        "maquina1": maq1, "maquina2": maq2, "molino": molino
    }
}
mock_pack_teams = {
    "teams_by_type": {
        "empaque1": emp1, "empaque2": emp2, "empaque3": emp3, "empaque4": emp4,
        "maquina1": maq1, "maquina2": maq2
    }
}

def get_team_name(res):
    if 'selected_team' in res:
        return res['selected_team']['name']
    elif 'most_suitable_team' in res:
        team = res['most_suitable_team']
        # Handle if it's a dict or object (mock)
        if isinstance(team, dict):
            return team.get('name')
        return team.name
    return None

def test_manufacturing_rules():
    print("\n--- Testing Manufacturing Rules ---")
    rule = ManufacturedRule()
    db = MagicMock()

    with patch('app.modules.automation.services.utils.team_selection_service.TeamSelectionService.get_fabrication_teams', return_value=mock_fab_teams):
        
        # 1. BX < 13 -> Fabricado 3
        res = rule.get_most_suitable_team(db, {"code": "BX123", "quantity": 10})
        name = get_team_name(res)
        print(f"BX < 13: {name} (Expected: Fabricado 3)")
        assert name == 'Fabricado 3'

        # 2. BX > 13 -> Fabricado 1
        res = rule.get_most_suitable_team(db, {"code": "BX123", "quantity": 20})
        name = get_team_name(res)
        print(f"BX > 13: {name} (Expected: Fabricado 1)")
        assert name == 'Fabricado 1'

        # 3. M13 -> Fabricado 3
        res = rule.get_most_suitable_team(db, {"code": "ANY", "quantity": 50}, activity_type="M13")
        name = get_team_name(res)
        print(f"M13: {name} (Expected: Fabricado 3)")
        assert name == 'Fabricado 3'
        
        # 4. Liquid Keyword -> Fabricado 3
        res = rule.get_most_suitable_team(db, {"code": "ANY", "quantity": 50, "description": "JARABE DE FRESA"}, activity_type="M11")
        name = get_team_name(res)
        print(f"Liquid Keyword: {name} (Expected: Fabricado 3)")
        assert name == 'Fabricado 3'

        # 5. M12 -> Fabricado 1
        res = rule.get_most_suitable_team(db, {"code": "ANY", "quantity": 50}, activity_type="M12")
        name = get_team_name(res)
        print(f"M12: {name} (Expected: Fabricado 1)")
        assert name == 'Fabricado 1'
        
        # 6. M5 Specialists
        res = rule.get_most_suitable_team(db, {"code": "PTX1042", "quantity": 50}, activity_type="M5")
        name = get_team_name(res)
        print(f"M5 PTX1042: {name} (Expected: Fabricado 2)")
        assert name == 'Fabricado 2'

        res = rule.get_most_suitable_team(db, {"code": "FX999", "quantity": 50}, activity_type="M5")
        name = get_team_name(res)
        print(f"M5 FX Series: {name} (Expected: Fabricado 1)")
        assert name == 'Fabricado 1'
        
        # 7. M4 -> Maquina 1
        res = rule.get_most_suitable_team(db, {"code": "ANY", "quantity": 50}, activity_type="M4")
        name = get_team_name(res)
        print(f"M4: {name} (Expected: Maquina 1)")
        assert name == 'Maquina 1'


def test_packaging_rules():
    print("\n--- Testing Packaging Rules ---")
    rule = PackagingRule()
    db = MagicMock()

    with patch('app.modules.automation.services.utils.team_selection_service.TeamSelectionService.get_packaging_teams', return_value=mock_pack_teams), \
         patch('app.modules.automation.services.utils.team_selection_service.TeamSelectionService.get_fabrication_teams', return_value=mock_fab_teams):

        # 1. M1 -> Fabricado 3
        res = rule.get_most_suitable_team(db, {"code": "ANY", "quantity": 50}, activity_type="M1")
        name = get_team_name(res)
        print(f"M1: {name} (Expected: Fabricado 3)")
        assert name == 'Fabricado 3'
        
        # 2. M5 > 1000 -> Maquina 1
        res = rule.get_most_suitable_team(db, {"code": "ANY", "quantity": 1200}, activity_type="M5")
        name = get_team_name(res)
        print(f"M5 Qty 1200: {name} (Expected: Maquina 1)")
        assert name == 'Maquina 1'

        # 3. M5 <= 300 -> Empaque 1
        res = rule.get_most_suitable_team(db, {"code": "ANY", "quantity": 200}, activity_type="M5")
        name = get_team_name(res)
        print(f"M5 Qty 200: {name} (Expected: Empaque 1)")
        assert name == 'Empaque 1'

        # 4. M4 > 800 -> Empaque 2
        res = rule.get_most_suitable_team(db, {"code": "ANY", "quantity": 900}, activity_type="M4")
        name = get_team_name(res)
        print(f"M4 Qty 900: {name} (Expected: Empaque 2)")
        assert name == 'Empaque 2'
        
        # 5. Resto (M4 <= 800) -> Empaque 1
        res = rule.get_most_suitable_team(db, {"code": "ANY", "quantity": 500}, activity_type="M4")
        name = get_team_name(res)
        print(f"M4 Qty 500: {name} (Expected: Empaque 1)")
        assert name == 'Empaque 1'


def test_weighing_rules():
    print("\n--- Testing Weighing Rules ---")
    rule = WeighingRule()
    db = MagicMock()
    
    with patch('app.modules.automation.services.utils.team_selection_service.TeamSelectionService.get_weighing_team', return_value={"success": True, "most_suitable_team": pesado}):
        
        # 1. Qty <= 5 -> Included
        res = rule.get_most_suitable_team(db, {"quantity": 3}, activity_type="M7")
        print(f"Qty 3: Success={res.get('success')} (Expected: True)")
        assert res.get('success') == True
        
        # 2. Qty > 5 -> Excluded
        res = rule.get_most_suitable_team(db, {"quantity": 10}, activity_type="M7")
        print(f"Qty 10: Success={res.get('success')} (Reason: {res.get('reason')})")
        assert res.get('success') == False


if __name__ == "__main__":
    try:
        test_manufacturing_rules()
        test_packaging_rules()
        test_weighing_rules()
        print("\nALL TESTS PASSED")
    except AssertionError as e:
        print(f"\nTEST FAILED: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
