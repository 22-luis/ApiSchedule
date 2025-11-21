from typing import Dict, Any, List
from sqlalchemy.orm import Session
from app.modules.core.models.team import Team
from app.modules.programming.services.config import ServiceType, ServiceConfig

class TeamSelectionService:
    """
    Servicio para seleccionar el equipo más adecuado según el tipo de tarea.
    Utiliza la configuración centralizada para determinar prioridades.
    """
    
    @staticmethod
    def _get_team_by_priorities(db: Session, priorities: List[str], service_name: str) -> Dict[str, Any]:
        """
        Busca un equipo siguiendo una lista de prioridades.
        
        Args:
            db: Sesión de base de datos
            priorities: Lista de nombres (o partes de nombres) de equipos en orden de prioridad
            service_name: Nombre del servicio para mensajes de error
            
        Returns:
            Diccionario con el resultado de la búsqueda
        """
        teams = db.query(Team).all()
        
        for priority in priorities:
            for team in teams:
                if team.name and priority.lower() in team.name.lower():
                    return {
                        "success": True,
                        "most_suitable_team": {
                            "id": str(team.id),
                            "name": team.name,
                            "supervisorId": str(team.supervisorId) if team.supervisorId else None
                        },
                        "message": f"Equipo encontrado por prioridad '{priority}'"
                    }
                    
        return {
            "success": False,
            "message": f"No se encontró ningún equipo adecuado para {service_name}"
        }

    @staticmethod
    def get_weighing_team(db: Session) -> Dict[str, Any]:
        """Obtiene el equipo más adecuado para pesado"""
        priorities = ServiceConfig.get_team_priorities(ServiceType.WEIGHING)
        return TeamSelectionService._get_team_by_priorities(db, priorities, "pesado")

    @staticmethod
    def get_fabrication_team(db: Session) -> Dict[str, Any]:
        """Obtiene el equipo más adecuado para fabricación"""
        priorities = ServiceConfig.get_team_priorities(ServiceType.FABRICATION)
        result = TeamSelectionService._get_team_by_priorities(db, priorities, "fabricación")
        
        # Agregar conteo de equipos para compatibilidad
        if result.get("success"):
            # Contar cuántos equipos de fabricación hay en total
            fabrication_keywords = ["molino", "fabricado"]
            count = 0
            teams = db.query(Team).all()
            for team in teams:
                if team.name and any(k in team.name.lower() for k in fabrication_keywords):
                    count += 1
            result["total_fabrication_teams"] = count
            
        return result

    @staticmethod
    def get_fabrication_teams(db: Session) -> Dict[str, Any]:
        """
        Obtiene todos los equipos de fabricación organizados por tipo.
        Utilizado por las reglas de negocio de Manufactured.py.
        """
        teams = db.query(Team).all()
        teams_by_type = {}
        
        for team in teams:
            if not team.name:
                continue
                
            name_lower = team.name.lower()
            
            if "molino" in name_lower:
                teams_by_type["molino"] = team
            elif "fabricado 1" in name_lower or "maquina 1" in name_lower:
                teams_by_type["fabricado1"] = team
            elif "fabricado 2" in name_lower or "maquina 2" in name_lower:
                teams_by_type["fabricado2"] = team
            elif "fabricado 3" in name_lower:
                teams_by_type["fabricado3"] = team
                
        return {
            "success": True,
            "teams_by_type": teams_by_type,
            "count": len(teams_by_type)
        }

    @staticmethod
    def get_packaging_team(db: Session) -> Dict[str, Any]:
        """Obtiene el equipo más adecuado para empaque"""
        priorities = ServiceConfig.get_team_priorities(ServiceType.PACKAGING)
        result = TeamSelectionService._get_team_by_priorities(db, priorities, "empaque")
        
        # Agregar conteo de equipos para compatibilidad
        if result.get("success"):
            # Contar cuántos equipos de empaque hay en total
            packaging_keywords = ["empaque", "maquina"]
            count = 0
            teams = db.query(Team).all()
            for team in teams:
                if team.name and any(k in team.name.lower() for k in packaging_keywords):
                    count += 1
            result["total_packaging_teams"] = count
            
        return result
