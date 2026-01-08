"""
Script to fix mixed-case role values in the users table.
This script updates all lowercase role values to uppercase to match the PostgreSQL enum.
"""
import sys
import os
from pathlib import Path

# Add project root to path
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
sys.path.append(str(PROJECT_ROOT))
os.chdir(PROJECT_ROOT)

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

from sqlalchemy import create_engine, text
from app.shared.core.config import settings

def fix_roles():
    print(f"Connecting to database...")
    engine = create_engine(settings.SQLALCHEMY_DATABASE_URI)
    
    with engine.connect() as conn:
        # First, let's see what values we have
        result = conn.execute(text("SELECT DISTINCT role FROM users"))
        roles = [row[0] for row in result]
        print(f"Current distinct roles in users table: {roles}")
        
        # Update lowercase to uppercase
        role_mappings = [
            ('admin', 'ADMIN'),
            ('planner', 'PLANNER'),
            ('supervisor', 'SUPERVISOR'),
            ('timekeeper', 'TIMEKEEPER'),
            ('user', 'USER'),
            ('warehouse', 'WAREHOUSE'),
            ('accounting', 'ACCOUNTING'),
            ('qc_coordinator', 'QC_ENGINEER'),
            ('qc_assistant', 'QC_TECHNICIAN'),
            ('qc_engineer', 'QC_ENGINEER'),
            ('qc_technician', 'QC_TECHNICIAN'),
        ]
        
        for old_val, new_val in role_mappings:
            result = conn.execute(
                text("UPDATE users SET role = :new_val WHERE role = :old_val"),
                {"old_val": old_val, "new_val": new_val}
            )
            if result.rowcount > 0:
                print(f"Updated {result.rowcount} users from '{old_val}' to '{new_val}'")
        
        conn.commit()
        
        # Verify the fix
        result = conn.execute(text("SELECT DISTINCT role FROM users"))
        roles = [row[0] for row in result]
        print(f"\nAfter fix - distinct roles in users table: {roles}")

if __name__ == "__main__":
    fix_roles()
    print("\nDone! Restart the server if needed.")
