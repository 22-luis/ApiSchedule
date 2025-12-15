from app.shared.db.session import SessionLocal
from sqlalchemy import text

def list_teams():
    db = SessionLocal()
    try:
        result = db.execute(text("SELECT id, name FROM teams"))
        print("--- Available Teams ---")
        for row in result:
            print(f"Name: '{row.name}'")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    list_teams()
