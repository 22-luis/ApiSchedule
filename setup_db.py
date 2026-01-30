import sqlalchemy
from sqlalchemy import text, inspect
from app.shared.db.session import engine
import subprocess
import os

def run_command(command):
    print(f"Running: {command}")
    result = subprocess.run(command, shell=True, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Error: {result.stderr}")
    else:
        print(f"Output: {result.stdout}")
    return result.returncode

def fix_schema():
    print("Connecting to database...")
    with engine.connect() as conn:
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        
        if 'test_record' in tables:
            print("Checking test_record columns...")
            columns = inspector.get_columns('test_record')
            catalog_test_col = next((c for c in columns if c['name'] == 'catalog_test'), None)
            
            if catalog_test_col and not catalog_test_col['nullable']:
                print("Altering test_record.catalog_test to allow nulls...")
                conn.execute(text("ALTER TABLE test_record ALTER COLUMN catalog_test DROP NOT NULL"))
                conn.commit()
                print("Column catalog_test is now nullable.")
            else:
                print("catalog_test is already nullable or doesn't exist.")

    print("Running alembic upgrade head...")
    run_command(".venv\\Scripts\\alembic.exe upgrade head")

if __name__ == "__main__":
    fix_schema()
