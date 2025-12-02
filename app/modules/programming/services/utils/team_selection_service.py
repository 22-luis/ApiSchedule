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
            elif "fabricado 1" in name_lower:
                teams_by_type["fabricado1"] = team
            elif "fabricado 2" in name_lower:
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

    @staticmethod
    def get_packaging_teams(db: Session) -> Dict[str, Any]:
        """
        Obtiene todos los equipos de empaque organizados por tipo.
        Actualizado para soportar las reglas del flujograma.
        """
        teams = db.query(Team).all()
        teams_by_type = {}
        
        for team in teams:
            if not team.name:
                continue
                
            name_lower = team.name.lower()
            
            # Clasificación basada en nombres exactos de equipos
            if "empaque 1" in name_lower or "empaque1" in name_lower:
                teams_by_type["empaque1"] = team
            elif "empaque 2" in name_lower or "empaque2" in name_lower:
                teams_by_type["empaque2"] = team
            elif "empaque 3" in name_lower or "empaque3" in name_lower:
                teams_by_type["empaque3"] = team
            elif "empaque 4" in name_lower or "empaque4" in name_lower:
                teams_by_type["empaque4"] = team
            elif "maquina 1" in name_lower or "máquina 1" in name_lower:
                teams_by_type["maquina1"] = team
            elif "maquina 2" in name_lower or "máquina 2" in name_lower:
                teams_by_type["maquina2"] = team
            elif "empaque" in name_lower and "grupo" in name_lower:
                # Empaque Grupo puede ser un equipo genérico
                teams_by_type["empaque_grupo"] = team
            elif "empaque" in name_lower:
                # Fallback para equipos de empaque genéricos
                if "empaque_generic" not in teams_by_type:
                    teams_by_type["empaque_generic"] = team

        return {
            "success": True,
            "teams_by_type": teams_by_type,
            "count": len(teams_by_type)
        }

    @staticmethod
    def get_specific_packaging_team_for_activity(activity_name: str, activity_description: str, teams_data: Dict) -> Dict[str, Any]:
        """
        Selecciona el equipo específico basado en la actividad.
        """
        teams_by_type = teams_data.get("teams_by_type", {})
        activity_upper = activity_name.upper()
        
        selected_team = None
        reason = ""
        rule_applied = ""

        # Logic from packaging.py priorities
        if "GRUPO" in activity_upper:
            selected_team = teams_by_type.get("empaque_grupo")
            reason = "Actividad de grupo asignada a Empaque Grupo"
            rule_applied = "empaque_grupo"
        elif "MANUAL" in activity_upper:
             selected_team = teams_by_type.get("empaque_manual")
             reason = "Actividad manual asignada a Empaque Manual"
             rule_applied = "empaque_manual"
        elif "SEMI" in activity_upper:
             selected_team = teams_by_type.get("empaque_semi")
             reason = "Actividad semi-automática asignada a Máquina 1"
             rule_applied = "empaque_semi"
        elif "AUTO" in activity_upper:
             selected_team = teams_by_type.get("empaque_auto")
             reason = "Actividad automática asignada a Máquina 2"
             rule_applied = "empaque_auto"
        elif "MEZCLA" in activity_upper:
             selected_team = teams_by_type.get("empaque_mezcla")
             reason = "Actividad de mezcla asignada a Empaque 2"
             rule_applied = "empaque_mezcla"
        
        # Fallback
        if not selected_team:
             # Try to find any team
             if teams_by_type:
                 # Prefer empaque_grupo if available as fallback
                 if "empaque_grupo" in teams_by_type:
                     selected_team = teams_by_type["empaque_grupo"]
                     reason = "Fallback: Asignado a Empaque Grupo por defecto"
                     rule_applied = "fallback_grupo"
                 else:
                     selected_team = next(iter(teams_by_type.values()))
                     reason = "Fallback: Asignado a primer equipo disponible"
                     rule_applied = "fallback_any"
        
        if selected_team:
            return {
                "success": True,
                "selected_team": {
                    "id": str(selected_team.id),
                    "name": selected_team.name,
                    "type": rule_applied
                },
                "reason": reason,
                "rule_applied": rule_applied
            }
            
        return {
            "success": False,
            "message": f"No se encontró equipo adecuado para la actividad {activity_name}"
        }
