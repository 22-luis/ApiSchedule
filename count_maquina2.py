
from app.shared.db.session import SessionLocal
from sqlalchemy import text
import json

db = SessionLocal()
try:
    sql = text("""
        SELECT p.id, tm.name, COUNT(pt.task_id) as task_count
        FROM programming p
        JOIN teams tm ON p.team_id = tm.id
        LEFT JOIN programming_task pt ON p.id = pt.programming_id
        WHERE tm.name = 'MAQUINA 2' AND p.date = '2026-02-11'
        GROUP BY p.id, tm.name
    """)
    result = db.execute(sql).fetchall()
    data = [dict(r._mapping) for r in result]
    print(json.dumps([{k: str(v) for k,v in d.items()} for d in data], indent=2))
finally:
    db.close()
