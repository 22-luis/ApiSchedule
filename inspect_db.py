from sqlalchemy import create_engine, inspect
from app.core.config import settings

def inspect_tables():
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
