import sys
import os

# Add the project root to the python path
sys.path.append(os.getcwd())

from app.shared.db.session import SessionLocal
from app.modules.programming.services.utils.programming_utils import ProgrammingUtils
from app.shared.utils.Auto.rules.weighning import WeighingRule
from app.shared.utils.Auto.rules.Manufactured import ManufacturedRule
from app.shared.utils.Auto.rules.packaging import PackagingRule

def test_activity_filtering():
    db = SessionLocal()
    try:
        # Test with a specific code
        test_code = "A5017"
        
        print(f"--- TESTING ACTIVITY FILTERING FOR CODE: {test_code} ---\n")
        
        # Get activities for this code
        activities_result = ProgrammingUtils.get_activities_by_code(test_code, db)
        
        if not activities_result.get("success"):
            print(f"ERROR: {activities_result.get('message')}")
            return
        
        activities = activities_result.get("activities", [])
        print(f"Total activities found: {len(activities)}")
        for act in activities:
            print(f"  - Activity: {act['activity']}, Performance: {act['performance']}, Time: {act['time']}")
        
        # Test WeighingRule
        print("\n--- TESTING WEIGHING RULE ---")
        weighing_rule = WeighingRule()
        filtered_weighing = weighing_rule.filter_activities(activities)
        print(f"Filtered Weighing Activities: {len(filtered_weighing)}")
        for act in filtered_weighing:
            print(f"  - {act['activity']}")
        
        # Test ManufacturedRule
        print("\n--- TESTING MANUFACTURED RULE ---")
        manufactured_rule = ManufacturedRule()
        filtered_manufactured = manufactured_rule.filter_activities(activities)
        print(f"Filtered Manufactured Activities: {len(filtered_manufactured)}")
        for act in filtered_manufactured:
            print(f"  - {act['activity']}")
        
        # Test PackagingRule
        print("\n--- TESTING PACKAGING RULE ---")
        packaging_rule = PackagingRule()
        filtered_packaging = packaging_rule.filter_activities(activities)
        print(f"Filtered Packaging Activities: {len(filtered_packaging)}")
        for act in filtered_packaging:
            print(f"  - {act['activity']}")
        
        # Test get_activity_for_order for each service
        print("\n--- TESTING get_activity_for_order ---")
        
        test_order = {
            "lote": 91144,
            "code": test_code,
            "quantity": 100
        }
        
        print("\nWeighing:")
        weighing_activity = weighing_rule.get_activity_for_order(test_order, activities)
        print(f"  Result: {weighing_activity}")
        
        print("\nManufactured:")
        manufactured_activity = manufactured_rule.get_activity_for_order(test_order, activities)
        print(f"  Result: {manufactured_activity}")
        
        print("\nPackaging:")
        packaging_activity = packaging_rule.get_activity_for_order(test_order, activities)
        print(f"  Result: {packaging_activity}")

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    test_activity_filtering()
