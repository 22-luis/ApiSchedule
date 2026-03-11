
from app.shared.db.session import SessionLocal
from sqlalchemy import text
import json

db = SessionLocal()
try:
    sql = text("""
        SELECT p.id, tm.name, p.date, p.status
        FROM programming p
        JOIN teams tm ON p.team_id = tm.id
        WHERE p.date = '2026-02-11'
    """)
    result = db.execute(sql).fetchall()
    data = [dict(r._mapping) for r in result]
    print(json.dumps([{k: str(v) for k,v in d.items()} for d in data], indent=2))
finally:
    db.close()
