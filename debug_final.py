
from app.shared.db.session import SessionLocal
from sqlalchemy import text
import json

pid = '6b4c9dc1-77b5-45f3-9f68-8b480d334114e'
db = SessionLocal()
try:
    sql = text("SELECT COUNT(*) FROM programming_task WHERE programming_id = :pid")
    count = db.execute(sql, {"pid": pid}).scalar()
    
    sql_tasks = text("""
        SELECT t.description, t.minutes, pt.real_quantity 
        FROM programming_task pt 
        JOIN task t ON pt.task_id = t.id 
        WHERE pt.programming_id = :pid
    """)
    tasks = db.execute(sql_tasks, {"pid": pid}).fetchall()
    
    print(json.dumps({
        "count": count,
        "tasks": [dict(r._mapping) for r in tasks]
    }, indent=2, default=str))
finally:
    db.close()
