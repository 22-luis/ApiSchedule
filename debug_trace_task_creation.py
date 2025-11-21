import sys
import os
from sqlalchemy import text
from datetime import date

# Add the project root to the python path
sys.path.append(os.getcwd())

from app.shared.db.session import SessionLocal

def trace_task_creation():
    db = SessionLocal()
    try:
        # Get a sample order to trace
        print("--- CHECKING RECENT ORDERS ---")
        result = db.execute(text("SELECT lote, code, quantity, status FROM \"order\" ORDER BY lote DESC LIMIT 5"))
        orders = result.fetchall()
        print(f"Recent Orders:")
        for order in orders:
            print(f"  - Lote: {order.lote}, Code: {order.code}, Quantity: {order.quantity}, Status: {order.status}")
        
        if not orders:
            print("No orders found!")
            return
            
        # Check what activities exist for the codes
        print("\n--- CHECKING ACTIVITIES FOR ORDER CODES ---")
        for order in orders[:2]:  # Check first 2 orders
            result = db.execute(text("SELECT code, activity, type, performance FROM code WHERE code = :code"), {"code": order.code})
            activities = result.fetchall()
            print(f"\nCode: {order.code}")
            if activities:
                for act in activities:
                    print(f"  - Activity: {act.activity}, Type: {act.type}, Performance: {act.performance}")
            else:
                print(f"  - NO ACTIVITIES FOUND for code {order.code}")
        
        # Check tasks created
        print("\n--- CHECKING TASKS CREATED ---")
        result = db.execute(text("SELECT t.id, t.lote, t.activity, t.status, pt.programming_id FROM task t LEFT JOIN programming_task pt ON t.id = pt.task_id ORDER BY t.lote DESC LIMIT 10"))
        tasks = result.fetchall()
        print(f"Recent Tasks (Total: {len(tasks)}):")
        for task in tasks:
            print(f"  - Lote: {task.lote}, Activity: {task.activity}, Status: {task.status}, Programming: {task.programming_id}")
        
        # Check which programmings these tasks are in
        print("\n--- CHECKING PROGRAMMING ASSIGNMENTS ---")
        result = db.execute(text("""
            SELECT p.id, p.date, t.name as team_name, COUNT(pt.task_id) as task_count
            FROM programming p
            JOIN teams t ON p.team_id = t.id
            LEFT JOIN programming_task pt ON p.id = pt.programming_id
            WHERE p.date >= :today
            GROUP BY p.id, p.date, t.name
            ORDER BY p.date
            LIMIT 10
        """), {"today": date.today()})
        programmings = result.fetchall()
        print(f"Programmings with task counts:")
        for prog in programmings:
            print(f"  - Date: {prog.date}, Team: {prog.team_name}, Tasks: {prog.task_count}")

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    trace_task_creation()
