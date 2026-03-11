
from app.shared.db.session import SessionLocal
from app.modules.programming.models.programming import Programming, ProgrammingTask
from app.modules.programming.models.task import Task
from app.modules.organization.models.team import Team
from datetime import date
import json

db = SessionLocal()
try:
    team = db.query(Team).filter(Team.name == 'MAQUINA 2').first()
    if not team:
        print("Team MAQUINA 2 not found")
    else:
        prog = db.query(Programming).filter(
            Programming.team_id == team.id,
            Programming.date == date(2026, 2, 11)
        ).first()
        if not prog:
            print("Programming for 2026-02-11 not found")
        else:
            print(f"Programming ID: {prog.id}")
            tasks_data = []
            for pt in prog.programming_tasks:
                t = pt.task
                tasks_data.append({
                    "description": t.description or (t.code.description if t.code else "No Code"),
                    "minutes": t.minutes,
                    "quantity": t.quantity,
                    "real_quantity": pt.real_quantity,
                    "duration_in_hours": pt.duration_in_hours,
                    "real_start": str(pt.real_start_time) if pt.real_start_time else None,
                    "real_end": str(pt.real_end_time) if pt.real_end_time else None
                })
            print(json.dumps(tasks_data, indent=2))
finally:
    db.close()
