
from app.shared.db.session import SessionLocal
from sqlalchemy import text
import json

db = SessionLocal()
try:
    sql = text("""
        SELECT 
            t.description, 
            t.minutes, 
            t.quantity,
            pt.real_quantity,
            pt.duration_in_hours,
            pt.real_start_time,
            pt.real_end_time,
            c.code,
            c.time as code_time
        FROM programming_task pt
        JOIN task t ON pt.task_id = t.id
        LEFT JOIN code c ON t.code_id = c.id
        WHERE pt.programming_id = '6b4c9dc1-77b5-45f3-9f68-8b480d334114e'
    """)
    result = db.execute(sql).fetchall()
    data = [dict(r._mapping) for r in result]
    
    # Check if there's ANOTHER programming with tasks
    sql_check = text("""
        SELECT p.id, COUNT(pt.task_id) as count
        FROM programming p
        JOIN teams tm ON p.team_id = tm.id 
        JOIN programming_task pt ON p.id = pt.programming_id
        WHERE tm.name = 'MAQUINA 2' AND p.date = '2026-02-11'
        GROUP BY p.id
    """)
    check_result = db.execute(sql_check).fetchall()
    check_data = [dict(r._mapping) for r in check_result]

    print(json.dumps({
        "tasks": [ {k: str(v) for k,v in d.items()} for d in data ],
        "programming_with_tasks": [ {k: str(v) for k,v in d.items()} for d in check_data ]
    }, indent=2))
finally:
    db.close()
