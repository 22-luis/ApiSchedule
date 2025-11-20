
import sys
import os
from datetime import date, datetime, timedelta

# Add the project root to the python path
sys.path.append(os.getcwd())

# Manually load .env
env_path = os.path.join(os.getcwd(), ".env")
if os.path.exists(env_path):
    print(f"Loading .env from {env_path}")
    with open(env_path, "r") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                key, value = line.split("=", 1)
                os.environ[key] = value
else:
    print(".env file not found")

from app.db.session import SessionLocal
from app.models.programming import Programming, ProgrammingTask, ProgrammingStatus
from app.models.team import Team
from app.services.utils.programming_utils import ProgrammingUtils

def debug_schedule():
    db = SessionLocal()
    try:
        print(f"Current date.today(): {date.today()}")
        print(f"Current datetime.now(): {datetime.now()}")
        
        target_date = date(2025, 11, 20)
        print(f"Checking programmings for: {target_date}")
        
        programmings = db.query(Programming).filter(Programming.date == target_date).all()
        
        if not programmings:
            print("No programmings found for this date.")
        else:
            for p in programmings:
                team = db.query(Team).filter(Team.id == p.team_id).first()
                team_name = team.name if team else "Unknown"
                print(f"Programming ID: {p.id}")
                print(f"  Team: {team_name} (ID: {p.team_id})")
                print(f"  Status: {p.status}")
                
                tasks = db.query(ProgrammingTask).filter(ProgrammingTask.programming_id == p.id).all()
                print(f"  Tasks count: {len(tasks)}")
                
                current_minutes = ProgrammingUtils.calculate_current_programming_time(tasks, p.date)
                print(f"  Current minutes: {current_minutes}")
                
                # Check availability logic
                from app.utils.business.programming_availability import get_programming_availability
                # Simulate a small task of 1 minute
                avail = get_programming_availability(db, str(p.id), 1.0)
                print(f"  Availability check (1 min task): {avail}")

    finally:
        db.close()

if __name__ == "__main__":
    debug_schedule()
