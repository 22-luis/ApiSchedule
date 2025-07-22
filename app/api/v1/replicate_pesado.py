# -*- coding: utf-8 -*-
"""
Lógica automática para replicar tareas en equipos de tipo 'pesado' cuando se asigna una tarea a un equipo 'fabricado' o 'molino' con ciertas actividades.
"""
from typing import List
from sqlalchemy.orm import Session
from app.models.team import Team
from app.models.task import Task
from app.models.programming import Programming
from datetime import datetime

# Actividades que disparan la lógica
def get_actividades_trigger():
    return {"MOLIENDA", "MEZCLAS", "MEZCLA LIQUIDA", "FABRICACION", "PESADO Y/ O FABRICADO"}

def get_team_type(team: Team) -> str:
    """
    Devuelve el tipo de equipo según el nombre (substring, no exacto).
    Ejemplo: 'fabricado 1', 'molino 2', 'pesado principal'...
    """
    name = (team.name or '').lower()
    if "fabricado" in name:
        return "fabricado"
    if "molino" in name:
        return "molino"
    if "pesado" in name:
        return "pesado"
    return "otro"

def replicate_task_to_pesado_if_needed(
    db: Session,
    original_task: Task,
    programming_date: datetime.date,
):
    """
    Si la tarea original es de un equipo 'fabricado' o 'molino' y la actividad está en el set,
    replica la tarea en el equipo 'pesado' correspondiente, evitando duplicados.
    """
    ACTIVIDADES_TRIGGER = get_actividades_trigger()
    # 1. Detectar tipo de equipo original
    original_teams: List[Team] = original_task.teams
    if not original_teams:
        return  # No hay equipo asignado

    # 2. ¿Algún equipo es 'fabricado' o 'molino'?
    trigger_team = next((t for t in original_teams if get_team_type(t) in {"fabricado", "molino"}), None)
    if not trigger_team:
        return  # No aplica

    # 3. ¿La actividad es relevante?
    if not original_task.activity or original_task.activity.upper() not in ACTIVIDADES_TRIGGER:
        return

    # 4. Buscar todos los equipos de tipo 'pesado'
    pesado_teams = db.query(Team).filter(Team.name.ilike('%pesado%')).all()
    if not pesado_teams:
        return  # No hay equipos de pesado

    # 5. Para cada equipo de pesado, buscar la programación de ese día
    for pesado_team in pesado_teams:
        programming = db.query(Programming).filter_by(team_id=pesado_team.id, date=programming_date).first()
        if not programming:
            # Si no existe, puedes crearla aquí si lo deseas
            continue

        # 6. Evitar duplicados: ¿ya existe una tarea con el mismo código y fecha en este equipo?
        existing = (
            db.query(Task)
            .join(Task.teams)
            .join(Task.programmings)
            .filter(
                Team.id == pesado_team.id,
                Programming.date == programming_date,
                Task.code_id == original_task.code_id,
            )
            .first()
        )
        if existing:
            continue  # Ya existe, no duplicar

        # 7. Crear la tarea para el equipo de pesado
        pesado_task = Task(
            code_id=original_task.code_id,
            lote=original_task.lote,
            quantity=original_task.quantity,
            specification=original_task.specification,
            preparation_id=original_task.preparation_id,
            minutes=None,  # O lógica propia
            start_time=None,
            end_time=None,
            people=None,
            performance=None,
            material=original_task.material,
            presentation=original_task.presentation,
            fabricationCode=original_task.fabricationCode,
            usefulLife=original_task.usefulLife,
            related_task_code=original_task.related_task_code,
            unit=original_task.unit,
            type=original_task.type,
            activity="PESADO Y/ O FABRICADO",
            description=original_task.description,
        )
        pesado_task.teams.append(pesado_team)
        db.add(pesado_task)
        db.flush()  # Para obtener el ID

        # Asociar a la programación del equipo pesado
        programming.tasks.append(pesado_task)
        db.commit() 