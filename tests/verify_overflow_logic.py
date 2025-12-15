
import sys
import os
from unittest.mock import MagicMock, patch

# Add the project root to the python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.modules.automation.rules.Manufactured import ManufacturedRule
from app.modules.automation.rules.packaging import PackagingRule

# Mock Team objects
fab1 = MagicMock(id='fab1_id'); fab1.name = 'Fabricado 1'
fab2 = MagicMock(id='fab2_id'); fab2.name = 'Fabricado 2'
fab3 = MagicMock(id='fab3_id'); fab3.name = 'Fabricado 3'
maq1 = MagicMock(id='maq1_id'); maq1.name = 'Maquina 1'
maq2 = MagicMock(id='maq2_id'); maq2.name = 'Maquina 2'
emp1 = MagicMock(id='emp1_id'); emp1.name = 'Empaque 1'
emp2 = MagicMock(id='emp2_id'); emp2.name = 'Empaque 2'
emp3 = MagicMock(id='emp3_id'); emp3.name = 'Empaque 3'

mock_fab_teams = {"teams_by_type": {"fabricado1": fab1, "fabricado2": fab2, "fabricado3": fab3, "maquina1": maq1, "maquina2": maq2}}
mock_pack_teams = {"teams_by_type": {"empaque1": emp1, "empaque2": emp2, "empaque3": emp3, "maquina1": maq1, "maquina2": maq2}}

def test_overflow_candidates():
    print("\n--- Testing Overflow Logic (Candidate Selection) ---")
    fab_rule = ManufacturedRule()
    pack_rule = PackagingRule()
    db = MagicMock()

    with patch('app.modules.automation.services.utils.team_selection_service.TeamSelectionService.get_fabrication_teams', return_value=mock_fab_teams), \
         patch('app.modules.automation.services.utils.team_selection_service.TeamSelectionService.get_packaging_teams', return_value=mock_pack_teams), \
         patch('app.modules.automation.services.utils.team_selection_service.TeamSelectionService.get_weighing_team', return_value={"success": True, "most_suitable_team": {"id": "pesado_id", "name": "PESADO"}}):

        # 1. Fab: BX > 13 -> [Fab1, Fab2]
        cands = fab_rule.get_candidate_teams(db, {"code": "BX123", "quantity": 20})
        names = [c['name'] for c in cands]
        print(f"Fab BX > 13: {names}")
        assert names == ['Fabricado 1', 'Fabricado 2']
        
        # 2. Fab: M12 -> [Fab1, Fab2]
        cands = fab_rule.get_candidate_teams(db, {"code": "ANY", "quantity": 100}, activity_type="M12")
        names = [c['name'] for c in cands]
        print(f"Fab M12: {names}")
        assert names == ['Fabricado 1', 'Fabricado 2']

        # 3. Fab: Fallback -> [Fab1, Fab2, Fab3]
        cands = fab_rule.get_candidate_teams(db, {"code": "OTHER", "quantity": 100}, activity_type="OTHER")
        names = [c['name'] for c in cands]
        print(f"Fab Fallback: {names}")
        assert names == ['Fabricado 1', 'Fabricado 2', 'Fabricado 3']

        # 4. Pack: M5 > 600 -> [Maq1, Maq2]
        cands = pack_rule.get_candidate_teams(db, {"code": "ANY", "quantity": 700}, activity_type="M5")
        names = [c['name'] for c in cands]
        print(f"Pack M5 > 600: {names}")
        assert names == ['Maquina 1', 'Maquina 2']

        # 5. Pack: M5 <= 300 -> [Emp1, Emp3]
        cands = pack_rule.get_candidate_teams(db, {"code": "ANY", "quantity": 200}, activity_type="M5")
        names = [c['name'] for c in cands]
        print(f"Pack M5 <= 300: {names}")
        assert names == ['Empaque 1', 'Empaque 3']

        # 6. Pack: M4 < 800 -> [Emp2, Emp1]
        cands = pack_rule.get_candidate_teams(db, {"code": "ANY", "quantity": 700}, activity_type="M4")
        names = [c['name'] for c in cands]
        print(f"Pack M4 < 800: {names}")
        assert names == ['Empaque 2', 'Empaque 1']

        # 7. Pack: Resto -> [Emp1, Emp3, Maq1]
        cands = pack_rule.get_candidate_teams(db, {"code": "ANY", "quantity": 900}, activity_type="M4")
        names = [c['name'] for c in cands]
        print(f"Pack Resto: {names}")
        assert names == ['Empaque 1', 'Empaque 3', 'Maquina 1']


if __name__ == "__main__":
    try:
        test_overflow_candidates()
        print("\nALL OVERFLOW TESTS PASSED")
    except AssertionError as e:
        print(f"\nTEST FAILED: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
