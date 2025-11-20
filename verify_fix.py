import sys
import os
from datetime import date
from dotenv import load_dotenv

# Load env vars
load_dotenv()

from app.db.session import SessionLocal
from app.services.utils.programming_utils import ProgrammingUtils
from app.models.team import Team
from app.models.programming import Programming

def verify():
    db = SessionLocal()
    try:
        teams = db.query(Team).all()
        for team in teams:
            print(f"\nTesting with team: {team.name} (ID: {team.id})")
            
            today = date.today()
            
            # Call the function
            programmings = ProgrammingUtils.get_available_programmings_for_team(str(team.id), db)
            
            found_today = False
            for p in programmings:
                if p['date'] == today.isoformat():
                    found_today = True
                    break
                    
            if found_today:
                print(f"SUCCESS: Found programming for today for team {team.name}")
            else:
                # Check if it exists in DB
                prog = db.query(Programming).filter(Programming.team_id == team.id, Programming.date == today).first()
                if prog:
                    print(f"Programming for today exists with status: {prog.status}")
                else:
                    print(f"Programming for today does NOT exist. It should have been created if possible.")
                    # Check if future programmings exist
                    if programmings:
                        print(f"Future programmings exist (first: {programmings[0]['date']}). Gap detected and NOT filled?")
                    else:
                        print("No future programmings either.")
                
    finally:
        db.close()

if __name__ == "__main__":
    verify()
