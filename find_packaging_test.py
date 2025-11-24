
from app.shared.db.session import SessionLocal
from sqlalchemy import text

def find_packaging_order():
    db = SessionLocal()
    try:
        print("--- Searching for PACKAGING candidates ---")
        sql = text("""
            SELECT o.lote, o.code, c.activity 
            FROM "order" o 
            JOIN code c ON o.code = c.code 
            WHERE c.activity LIKE '%EMPAQUE%' 
            AND c.activity NOT LIKE '%PESADO%'
            ORDER BY o.lote DESC 
            LIMIT 5
        """)
        results = db.execute(sql).fetchall()
        if results:
            for r in results:
                print(f"Candidate: Lote={r[0]}, Code={r[1]}, Activity={r[2]}")
        else:
            print("No pure Packaging candidates found.")

    except Exception as e:
        print(f"Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    find_packaging_order()
