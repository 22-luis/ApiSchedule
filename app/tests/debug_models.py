
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

try:
    print("Importing User...")
    from app.modules.organization.models.user import User
    print("Importing Team...")
    from app.modules.organization.models.team import Team
    print("Importing Code...")
    from app.modules.codes.models.code import Code
    print("Importing Preparation...")
    from app.modules.programming.models.preparation import Preparation
    print("Importing Programming...")
    from app.modules.programming.models.programming import Programming, ProgrammingTask
    print("Importing Task...")
    from app.modules.programming.models.task import Task
    print("Importing Order...")
    from app.modules.orders.models.order import Order
    
    print("All imports successful.")
    
    from app.shared.db.session import SessionLocal
    db = SessionLocal()
    print("Session created.")
    
except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
