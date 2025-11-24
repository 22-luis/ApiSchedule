import sys
import os
from pathlib import Path

# Add project root to path
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
sys.path.append(str(PROJECT_ROOT))

from sqlalchemy import create_engine, inspect
from app.shared.core.config import settings

def inspect_tables():
    print(f"Connecting to: {settings.SQLALCHEMY_DATABASE_URI}")
    engine = create_engine(settings.SQLALCHEMY_DATABASE_URI)
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    print("Tables:", tables)
    
    if "user_teams" in tables:
        print("user_teams exists")
    else:
        print("user_teams does not exist")
        
    if "user_team_association" in tables:
        print("user_team_association exists")
    else:
        print("user_team_association does not exist")

if __name__ == "__main__":
    inspect_tables()
