import sys
import os
from sqlalchemy import text
from datetime import date

# Add the project root to the python path
sys.path.append(os.getcwd())

from app.shared.db.session import SessionLocal
from app.modules.programming.services.config import ServiceType, ServiceConfig

def check_data():
    db = SessionLocal()
    try:
        print("--- CHECKING TEAMS (Raw SQL) ---")
        result = db.execute(text("SELECT id, name FROM teams"))
        teams = result.fetchall()
        print(f"Total Teams: {len(teams)}")
        for team in teams:
            print(f"  - ID: {team.id}, Name: {team.name}")
            
        print("\n--- CHECKING CODES (Raw SQL - Sample) ---")
        result = db.execute(text("SELECT code, activity, type FROM code LIMIT 10"))
        codes = result.fetchall()
        print(f"Total Codes (showing first 10): {len(codes)}")
        for code in codes:
            print(f"  - Code: {code.code}, Activity: {code.activity}, Type: {code.type}")

        print("\n--- CHECKING AVAILABLE PROGRAMMINGS (Raw SQL - Future) ---")
        # Note: adjusting for potential date formatting or type issues in raw SQL
        result = db.execute(text("SELECT p.id, p.date, t.name FROM programming p JOIN teams t ON p.team_id = t.id WHERE p.status = 'available' AND p.date >= :today ORDER BY p.date"), {"today": date.today()})
        programmings = result.fetchall()
        
        print(f"Total Available Programmings (Today+): {len(programmings)}")
        for prog in programmings:
            print(f"  - ID: {prog.id}, Date: {prog.date}, Team: {prog.name}")

        print("\n--- CHECKING CONFIGURATION ---")
        print(f"Weighing Keywords: {ServiceConfig.get_activity_keywords(ServiceType.WEIGHING)}")
        print(f"Fabrication Keywords: {ServiceConfig.get_activity_keywords(ServiceType.FABRICATION)}")
        print(f"Packaging Keywords: {ServiceConfig.get_activity_keywords(ServiceType.PACKAGING)}")

    except Exception as e:
        print(f"Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    check_data()
