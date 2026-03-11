
from app.shared.db.session import SessionLocal
from sqlalchemy import text
import json

db = SessionLocal()
try:
    sql = text("""
        SELECT 
            t.description, 
            t.id as task_id,
            t.minutes, 
            t.quantity,
            pt.real_quantity,
            pt.duration_in_hours,
            pt.real_start_time,
            pt.real_end_time,
            c.code
        FROM programming_task pt
        JOIN task t ON pt.task_id = t.id
        LEFT JOIN code c ON t.code_id = c.id
        WHERE pt.programming_id = 'a994e596-4b9e-4b75-8130-27f6a6a6744a'
    """)
    result = db.execute(sql).fetchall()
    data = [dict(r._mapping) for r in result]
    print(json.dumps([{k: str(v) for k,v in d.items()} for d in data], indent=2))
finally:
    db.close()
