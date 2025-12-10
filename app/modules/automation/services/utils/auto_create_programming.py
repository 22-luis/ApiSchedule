"""
Utilidades para la creación automática de programaciones.
"""

from typing import Dict, Any
from sqlalchemy.orm import Session
from datetime import date
import logging

from app.modules.programming.models.programming import Programming
from app.modules.programming.models.state import ProgrammingStatus

logger = logging.getLogger(__name__)


def create_programming_if_not_exists(db: Session, team_id: str, programming_date: date) -> Dict[str, Any]:
    """
    Crea una programación automáticamente si no existe para un equipo y fecha específicos.
    
    Args:
        db: Sesión de base de datos
        team_id: ID del equipo
        programming_date: Fecha de la programación
        
    Returns:
        Diccionario con información de la programación:
        {
            "success": bool,
            "programming": Programming object or None,
            "created": bool,  # True si se creó, False si ya existía
            "message": str
        }
    """
    try:
        # Verificar si ya existe la programación
        existing_programming = db.query(Programming).filter(
            Programming.team_id == team_id,
            Programming.date == programming_date
        ).first()
        
        if existing_programming:
            logger.info(f"Programming already exists for team {team_id} on {programming_date}")
            return {
                "success": True,
                "programming": existing_programming,
                "created": False,
                "message": f"Programming already exists for team on {programming_date}"
            }
        
        # Crear nueva programación
        new_programming = Programming(
            date=programming_date,
            team_id=team_id,
            status=ProgrammingStatus.available
        )
        
        db.add(new_programming)
        db.commit()
        db.refresh(new_programming)
        
        logger.info(f"Created new programming {new_programming.id} for team {team_id} on {programming_date}")
        
        return {
            "success": True,
            "programming": new_programming,
            "created": True,
            "message": f"Created new programming for team on {programming_date}"
        }
        
    except Exception as e:
        logger.error(f"Error creating programming for team {team_id} on {programming_date}: {str(e)}")
        db.rollback()
        return {
            "success": False,
            "programming": None,
            "created": False,
            "message": f"Error creating programming: {str(e)}"
        }
