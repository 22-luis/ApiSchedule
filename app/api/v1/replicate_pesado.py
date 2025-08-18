# -*- coding: utf-8 -*-
"""
Lógica automática para replicar tareas en equipos de tipo 'pesado' cuando se asigna una tarea a un equipo 'fabricado' o 'molino' con ciertas actividades.
"""
import logging
from typing import List
from sqlalchemy.orm import Session
from app.models.team import Team
from app.models.task import Task
from app.models.programming import Programming, ProgrammingTask
from app.models.code import Code
from datetime import datetime

# Configurar logger
logger = logging.getLogger(__name__)

# Actividades que disparan la lógica
def get_actividades_trigger():
    return {
        "MOLIENDA EN POLVO",
        "MOLIENDA EN PASTA",
        "MEZCLA MANUAL POLVO",
        "MEZCLA EN MAQUINA",
        "MEZCLA LIQUIDA",
        "FABICACION DE ADEREZOS, JALEAS"
    }

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

def get_pesado_data_for_code(db: Session, code_id: str) -> dict:
    """
    Obtiene los datos específicos para la actividad PESADO basado en el código.
    Si no existe un código específico para PESADO, usa los datos del código original.
    """
    # Primero obtener el código original para saber el código base
    original_code = db.query(Code).filter(Code.id == code_id).first()
    if not original_code:
        logger.warning(f"❌ No se encontró código original con ID: {code_id}")
        return None
    
    logger.info(f"🔍 Buscando código PESADO para código base: {original_code.code}")
    
    # Buscar si existe un código específico para PESADO con el mismo código base
    pesado_code = db.query(Code).filter(
        Code.code == original_code.code,
        Code.activity == "PESADO"
    ).first()
    
    if pesado_code:
        logger.info(f"✅ Encontrado código específico para PESADO: {pesado_code.code} (ID: {pesado_code.id})")
        logger.info(f"📋 Datos PESADO - Personas: {pesado_code.people}, Rendimiento: {pesado_code.performance}, Tipo: {pesado_code.type}")
        return {
            'code_id': pesado_code.id,  # Usar el ID del código PESADO
            'time': pesado_code.time,
            'people': pesado_code.people,
            'performance': pesado_code.performance,
            'material': pesado_code.material,
            'presentation': pesado_code.presentation,
            'fabricationCode': pesado_code.fabricationCode,
            'usefulLife': pesado_code.usefulLife,
            'related_code_team': pesado_code.related_code_team,
            'unit': pesado_code.unit,
            'type': pesado_code.type,
            'description': pesado_code.description
        }
    else:
        logger.info(f"⚠️ No se encontró código específico para PESADO, usando datos del código original")
        # Usar datos del código original pero con actividad PESADO
        return {
            'code_id': original_code.id,  # Mantener el ID del código original
            'time': original_code.time,
            'people': original_code.people,
            'performance': original_code.performance,
            'material': original_code.material,
            'presentation': original_code.presentation,
            'fabricationCode': original_code.fabricationCode,
            'usefulLife': original_code.usefulLife,
            'related_code_team': original_code.related_code_team,
            'unit': original_code.unit,
            'type': original_code.type,
            'description': original_code.description
        }

def replicate_task_to_pesado_if_needed(
    db: Session,
    original_task: Task,
    programming_date: datetime.date,
):
    """
    Si la tarea original es de un equipo 'fabricado' o 'molino' y la actividad está en el set,
    replica la tarea en el equipo 'pesado' correspondiente, evitando duplicados.
    """
    logger.info(f"🔍 Iniciando replicación para tarea {original_task.id} con actividad '{original_task.activity}'")
    
    ACTIVIDADES_TRIGGER = get_actividades_trigger()
    
    # 1. Detectar tipo de equipo original
    original_teams: List[Team] = original_task.teams
    if not original_teams:
        logger.warning("❌ No hay equipos asignados a la tarea original")
        return  # No hay equipo asignado

    logger.info(f"📋 Equipos originales: {[team.name for team in original_teams]}")

    # 2. ¿Algún equipo es 'fabricado' o 'molino'?
    trigger_team = next((t for t in original_teams if get_team_type(t) in {"fabricado", "molino"}), None)
    if not trigger_team:
        logger.info("❌ No se encontró equipo fabricado o molino")
        return  # No aplica

    logger.info(f"✅ Equipo trigger encontrado: {trigger_team.name} (tipo: {get_team_type(trigger_team)})")

    # 3. ¿La actividad es relevante?
    if not original_task.activity:
        logger.warning("❌ La tarea no tiene actividad definida")
        return
    
    activity_upper = original_task.activity.upper()
    logger.info(f"🔍 Verificando actividad: '{original_task.activity}' (upper: '{activity_upper}')")
    logger.info(f"📋 Actividades trigger: {ACTIVIDADES_TRIGGER}")
    
    if activity_upper not in ACTIVIDADES_TRIGGER:
        logger.info(f"❌ Actividad '{activity_upper}' no está en la lista de triggers")
        return

    logger.info(f"✅ Actividad '{activity_upper}' es válida para replicación")

    # 4. Obtener datos específicos para PESADO
    if not original_task.code_id:
        logger.warning("❌ La tarea original no tiene código asociado")
        return
    
    pesado_data = get_pesado_data_for_code(db, original_task.code_id)
    if not pesado_data:
        logger.warning(f"❌ No se pudieron obtener datos para PESADO del código {original_task.code_id}")
        return
    
    logger.info(f"📋 Datos obtenidos para PESADO: {pesado_data}")

    # 5. Buscar todos los equipos de tipo 'pesado'
    pesado_teams = db.query(Team).filter(Team.name.ilike('%pesado%')).all()
    if not pesado_teams:
        logger.warning("❌ No se encontraron equipos de tipo 'pesado'")
        return  # No hay equipos de pesado

    logger.info(f"📋 Equipos pesado encontrados: {[team.name for team in pesado_teams]}")

    # 6. Para cada equipo de pesado, buscar la programación de ese día
    for pesado_team in pesado_teams:
        logger.info(f"🔍 Procesando equipo pesado: {pesado_team.name}")
        
        programming = db.query(Programming).filter_by(team_id=pesado_team.id, date=programming_date).first()
        if not programming:
            logger.warning(f"❌ No existe programación para {pesado_team.name} en fecha {programming_date}")
            # Crear la programación si no existe
            try:
                programming = Programming(
                    team_id=pesado_team.id,
                    date=programming_date
                )
                db.add(programming)
                db.flush()
                logger.info(f"✅ Creada nueva programación para {pesado_team.name}")
            except Exception as e:
                logger.error(f"❌ Error creando programación: {e}")
                continue

        # 7. Evitar duplicados: ¿ya existe una tarea con el mismo código y fecha en este equipo?
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
            logger.info(f"⚠️ Ya existe tarea con código {original_task.code_id} en {pesado_team.name}")
            continue  # Ya existe, no duplicar

        # 8. Crear la tarea para el equipo de pesado usando datos específicos de PESADO
        try:
            pesado_task = Task(
                code_id=pesado_data['code_id'],  # Usar el ID del código PESADO específico
                lote=original_task.lote,        # Mismo lote
                quantity=original_task.quantity, # Misma cantidad
                specification=original_task.specification, # Misma especificación
                preparation_id=original_task.preparation_id, # Misma preparación
                # Usar datos específicos para PESADO
                minutes=pesado_data['time'],  # Tiempo específico para PESADO
                start_time=None,  # Se calculará después
                end_time=None,    # Se calculará después
                people=pesado_data['people'],  # Personas específicas para PESADO
                performance=pesado_data['performance'],  # Rendimiento específico para PESADO
                material=pesado_data['material'],  # Material específico para PESADO
                presentation=pesado_data['presentation'],  # Presentación específica para PESADO
                fabricationCode=pesado_data['fabricationCode'],  # Código de fabricación específico para PESADO
                usefulLife=pesado_data['usefulLife'],  # Vida útil específica para PESADO
                related_task_code=pesado_data['related_code_team'],  # Código relacionado específico para PESADO
                unit=pesado_data['unit'],  # Unidad específica para PESADO
                type=pesado_data['type'],  # Tipo específico para PESADO
                activity="PESADO",  # Actividad específica para pesado
                description=pesado_data['description'],  # Descripción específica para PESADO
                created_by_user_id=original_task.created_by_user_id  # Mismo usuario creador
            )
            
            # Asignar el equipo pesado
            pesado_task.teams = [pesado_team]
            
            db.add(pesado_task)
            db.flush()  # Para obtener el ID
            
            logger.info(f"✅ Tarea pesado creada con ID: {pesado_task.id}")

            # 9. Crear la asociación ProgrammingTask
            # Obtener el siguiente orden
            max_order = db.query(ProgrammingTask).filter(
                ProgrammingTask.programming_id == programming.id
            ).count()
            
            programming_task = ProgrammingTask(
                programming_id=programming.id,
                task_id=pesado_task.id,
                order=max_order + 1,
                start_time=None,
                end_time=None
            )
            
            db.add(programming_task)
            db.commit()
            
            logger.info(f"✅ Tarea replicada exitosamente en {pesado_team.name} con orden {max_order + 1}")
            logger.info(f"📋 Datos de la tarea pesado: actividad='PESADO', minutos={pesado_task.minutes}, personas={pesado_task.people}")
            
        except Exception as e:
            logger.error(f"❌ Error creando tarea pesado: {e}")
            db.rollback()
            continue 