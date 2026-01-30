import sqlalchemy
from app.shared.db.session import engine
from sqlalchemy import text

def fix_alembic_version():
    target_version = '3332f46ab036'
    with engine.connect() as connection:
        # Delete current version
        connection.execute(text("DELETE FROM alembic_version"))
        # Insert target version
        connection.execute(text(f"INSERT INTO alembic_version (version_num) VALUES ('{target_version}')"))
        connection.commit()
        print(f"Updated Alembic Version to: {target_version}")

if __name__ == "__main__":
    fix_alembic_version()
