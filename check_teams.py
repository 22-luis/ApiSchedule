from app.shared.db.session import SessionLocal
from app.modules.core.models.team import Team

def list_teams():
    db = SessionLocal()
    teams = db.query(Team).all()
    print("--- Available Teams ---")
    for t in teams:
        print(f"ID: {t.id}, Name: '{t.name}'")
    db.close()

if __name__ == "__main__":
    list_teams()
