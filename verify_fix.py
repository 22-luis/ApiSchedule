"""
Script to verify the fix for check_programming_availability.
"""
import sys
import os
from datetime import date, datetime, time, timedelta

# Add the project root to the python path
sys.path.append(os.getcwd())

from app.shared.db.session import SessionLocal
from app.modules.programming.models.programming import Programming, ProgrammingTask
from app.modules.programming.models.task import Task
from app.shared.utils.business.programming_availability import check_programming_availability, restore_programmings_availability

def verify_friday_fix():
    db = SessionLocal()
    try:
        # 1. Simulate the Friday scenario
        # Date: 2025-12-05 (Friday)
        # Tasks: 
        # - Task 1: 35 mins (7:00 - 7:35)
        # - Task 2: 60 mins (7:35 - 8:35)
        # End time: 8:35 AM = 515 minutes
        
        print("--- Verifying Fix for Friday 12/05/2025 ---")
        
        # Find the programming
        programming = db.query(Programming).filter(
            Programming.date == date(2025, 12, 5)
        ).first()
        
        if not programming:
            print("Programming for 2025-12-05 not found in DB.")
            return

        print(f"Programming ID: {programming.id}")
        print(f"Current Status: {programming.status}")
        
        # Check tasks
        tasks = db.query(ProgrammingTask).filter(ProgrammingTask.programming_id == programming.id).all()
        last_end_time = None
        for t in tasks:
            if t.end_time:
                if last_end_time is None or t.end_time > last_end_time:
                    last_end_time = t.end_time
        
        print(f"Last Task End Time: {last_end_time}")
        
        if last_end_time:
            end_minutes = last_end_time.hour * 60 + last_end_time.minute
            print(f"End Minutes: {end_minutes}")
            
            # Manual check of the logic
            STANDARD_START = 420
            DURATION = 460
            TOLERANCE = 10
            MAX_ALLOWED = STANDARD_START + DURATION + TOLERANCE
            print(f"Max Allowed (Calculated): {MAX_ALLOWED} (should be 890)")
            
            is_available_manual = end_minutes <= MAX_ALLOWED
            print(f"Is Available (Manual Check): {is_available_manual}")
            
        # Run the actual function
        is_available_func = check_programming_availability(db, programming)
        print(f"check_programming_availability() returns: {is_available_func}")
        
        if is_available_func:
            print("\n✅ SUCCESS: The function correctly identifies the programming as AVAILABLE.")
            
            # Restore availability
            print("Running restore_programmings_availability()...")
            restore_programmings_availability(db)
            db.refresh(programming)
            print(f"New Status in DB: {programming.status}")
        else:
            print("\n❌ FAILURE: The function still thinks it is UNAVAILABLE.")

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    verify_friday_fix()
