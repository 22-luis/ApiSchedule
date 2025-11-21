import sys
import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Add the parent directory to sys.path to allow importing app modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.shared.core.config import settings

def verify_creation():
    engine = create_engine(settings.SQLALCHEMY_DATABASE_URI)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()

    lotes = ['88535', '88536']
    
    print(f"Checking data for lotes: {lotes}")
    print("-" * 50)

    for lote in lotes:
        print(f"Checking Lote: {lote}")
        
        # Check Order
        order_query = text('SELECT lote, status FROM "order" WHERE lote = :lote')
        order = db.execute(order_query, {"lote": int(lote)}).fetchone()
        
        if order:
            print(f"  Order Found: Lote={order.lote}, Status={order.status}")
            if order.status != 'programmed':
                print(f"  [WARNING] Order status is '{order.status}', expected 'programmed'")
        else:
            print(f"  [ERROR] Order not found!")

        # Check Task
        task_query = text('SELECT id, status, minutes FROM task WHERE lote = :lote')
        task = db.execute(task_query, {"lote": lote}).fetchone()
        
        if task:
            print(f"  Task Found: ID={task.id}, Status={task.status}, Minutes={task.minutes}")
            
            # Check ProgrammingTask
            pt_query = text('SELECT programming_id, start_time, end_time FROM programming_task WHERE task_id = :task_id')
            pt = db.execute(pt_query, {"task_id": task.id}).fetchone()
            
            if pt:
                print(f"  ProgrammingTask Found: ProgrammingID={pt.programming_id}")
                print(f"    Start Time: {pt.start_time}")
                print(f"    End Time: {pt.end_time}")
            else:
                print(f"  [ERROR] ProgrammingTask not found for Task ID {task.id}")
        else:
            print(f"  [ERROR] Task not found for Lote {lote}")
            
        print("-" * 50)

    db.close()

if __name__ == "__main__":
    verify_creation()
