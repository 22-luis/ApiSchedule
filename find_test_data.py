
from app.shared.db.session import SessionLocal
from app.modules.programming.models.order import Order
from app.modules.programming.models.code import Code
from sqlalchemy import text

def find_test_orders():
    db = SessionLocal()
    try:
        # Find an order with a code that has "PESADO" in activity
        print("--- Searching for WEIGHING candidate ---")
        sql_weighing = text("""
            SELECT o.lote, o.code, c.activity 
            FROM "order" o 
            JOIN code c ON o.code = c.code 
            WHERE c.activity LIKE '%PESADO%' 
            ORDER BY o.lote DESC 
            LIMIT 1
        """)
        result_weighing = db.execute(sql_weighing).fetchone()
        if result_weighing:
            print(f"Found Weighing Candidate: Lote={result_weighing[0]}, Code={result_weighing[1]}, Activity={result_weighing[2]}")
        else:
            print("No Weighing candidate found.")

        # Find an order with a code that has "EMPAQUE" in activity
        print("\n--- Searching for PACKAGING candidate ---")
        sql_packaging = text("""
            SELECT o.lote, o.code, c.activity 
            FROM "order" o 
            JOIN code c ON o.code = c.code 
            WHERE c.activity LIKE '%EMPAQUE%' 
            ORDER BY o.lote DESC 
            LIMIT 1
        """)
        result_packaging = db.execute(sql_packaging).fetchone()
        if result_packaging:
            print(f"Found Packaging Candidate: Lote={result_packaging[0]}, Code={result_packaging[1]}, Activity={result_packaging[2]}")
        else:
            print("No Packaging candidate found.")

    except Exception as e:
        print(f"Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    find_test_orders()
