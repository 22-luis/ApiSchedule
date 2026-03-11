
from app.shared.db.session import SessionLocal
from sqlalchemy import text
import json

db = SessionLocal()
try:
    sql = text("""
        SELECT 
            t.description, 
            t.minutes as task_minutes, 
            t.quantity as task_quantity,
            pt.real_quantity,
            pt.duration_in_hours,
            pt.real_start_time,
            pt.real_end_time,
            c.code,
            c.time as code_time
        FROM programming p
        JOIN teams tm ON p.team_id = tm.id
        JOIN programming_task pt ON p.id = pt.programming_id
        JOIN task t ON pt.task_id = t.id
        LEFT JOIN code c ON t.code_id = c.id
        WHERE tm.name = 'MAQUINA 2' AND p.date = '2026-02-11'
    """)
    result = db.execute(sql).fetchall()
    data = []
    for r in result:
        data.append(dict(r._mapping))
    
    # Also check RecordStopwatch for these tasks
    sql_stopwatch = text("""
        SELECT task_id, accumulated_duration
        FROM record_stopwatch
        WHERE task_id IN (
            SELECT pt.task_id
            FROM programming p
            JOIN teams tm ON p.team_id = tm.id
            JOIN programming_task pt ON p.id = pt.programming_id
            WHERE tm.name = 'MAQUINA 2' AND p.date = '2026-02-11'
        )
    """)
    stopwatch_result = db.execute(sql_stopwatch).fetchall()
    stopwatch_data = []
    for r in stopwatch_result:
        stopwatch_data.append(dict(r._mapping))

    print(json.dumps({
        "tasks": [ {k: str(v) if v is not None else None for k,v in d.items()} for d in data ],
        "stopwatch": [ {k: str(v) if v is not None else None for k,v in d.items()} for d in stopwatch_data ]
    }, indent=2))
finally:
    db.close()
