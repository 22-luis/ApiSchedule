import sqlalchemy
from app.shared.db.session import engine
from sqlalchemy import inspect

def check_db():
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    print(f"Tables: {tables}")
    for table in tables:
        columns = [c["name"] for c in inspector.get_columns(table)]
        print(f"Table {table} columns: {columns}")

if __name__ == "__main__":
    check_db()
