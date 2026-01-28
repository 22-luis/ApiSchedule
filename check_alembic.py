import sqlalchemy
from app.shared.db.session import engine
from sqlalchemy import text

def check_alembic_version():
    with engine.connect() as connection:
        result = connection.execute(text("SELECT * FROM alembic_version"))
        for row in result:
            print(f"Current Alembic Version: {row[0]}")

if __name__ == "__main__":
    check_alembic_version()
