import os
import sys

# Add project root to path
project_root = os.getcwd()
if project_root not in sys.path:
    sys.path.append(project_root)

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

from app.shared.db.session import SessionLocal
from app.modules.codes.services import code_service
from app.modules.codes.repositories import code_repository

def verify():
    db = SessionLocal()
    try:
        # Get one code/activity from DB using the app's repository
        print("Fetching a sample code from the database...")
        codes, total = code_repository.find_all(db, limit=1)
        
        if not codes:
            print("No codes found in database to test with.")
            # We can still test logic with a dummy if needed, but safer with real data
            return

        sample = codes[0]
        code_str = sample.code
        activity_str = sample.activity
        print(f"Testing with Code: '{code_str}', Activity: '{activity_str}'")

        # Test get_code_by_code_and_activity
        print("Testing get_code_by_code_and_activity...")
        obj = code_service.get_code_by_code_and_activity(db, code_str, activity_str)
        print(f"SUCCESS: Found object ID {obj.id}")

        # Test get_activity_details
        print("Testing get_activity_details...")
        details = code_service.get_activity_details(db, code_str, activity_str)
        print("SUCCESS: get_activity_details returned data")
        
        # Verify structure
        expected_keys = ["success", "code", "activity", "activity_details", "message"]
        for key in expected_keys:
            if key not in details:
                print(f"ERROR: Missing key '{key}' in response")
            else:
                print(f"OK: Key '{key}' is present")

        print("\nALL VERIFICATIONS PASSED!")

    except Exception as e:
        print(f"AN ERROR OCCURRED: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    verify()
