
from app.shared.db.session import SessionLocal
from sqlalchemy import text
import json

db = SessionLocal()
try:
    sql = text("SELECT * FROM programming_task LIMIT 5")
    result = db.execute(sql).fetchall()
    data = [dict(r._mapping) for r in result]
    print(json.dumps([{k: str(v) for k,v in d.items()} for d in data], indent=2))
finally:
    db.close()
