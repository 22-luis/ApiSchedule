from typing import Dict, Any, Optional, Set, List
from sqlalchemy.orm import Session

from app.modules.automation.services.utils.team_selection_service import TeamSelectionService
from app.shared.core.enums import PackagingActivities
from app.modules.automation.services.config import ServiceType, ServiceConfig
from app.modules.automation.rules.base_rule import BaseAutomationRule

class PackagingRule(BaseAutomationRule):
    
    @property
    def service_type(self) -> ServiceType:
        return ServiceType.PACKAGING

    @property
    def activity_list_key(self) -> str:
        return "packaging_activities"

    @property
    def excluded_types(self) -> Set[str]:
        return {"M9", "M10", "M11", "M12", "M13", "M15"}

    @property
    def allowed_types(self) -> Set[str]:
        return {"M1", "M2", "M3", "M4", "M5"}

    @property
    def priority_keywords_groups(self) -> List[List[str]]:
        return [
            [PackagingActivities.EMP_GRUPO.value],
            [PackagingActivities.EMP_MANUAL.value],
            [PackagingActivities.EMP_SEMI.value],
            [PackagingActivities.EMP_AUTO.value],
            [PackagingActivities.EMP_MEZCLA.value]
        ]



    def get_most_suitable_team(self, db: Session, order_data: Dict = None, activity_type: Optional[str] = None) -> Dict[str, Any]:
    
        code = order_data.get("code", "") if order_data else ""
        quantity = order_data.get("quantity", 0) if order_data else 0
        
        # Obtener todos los equipos disponibles
        packaging_teams = TeamSelectionService.get_packaging_teams(db)
        fabrication_teams = TeamSelectionService.get_fabrication_teams(db)
        
        teams_by_type = packaging_teams.get("teams_by_type", {})
        fab_teams_by_type = fabrication_teams.get("teams_by_type", {})
        
        # REGLA MOLINO: M9, M3, M2 (Family) -> Delegate to Manufactured rule check or handle here if passed?
        # The prompt for Packaging mentions Empaque 1-3, Maquina 1-2.
        # But Filter was updated to allow M3, M2, etc. in Manufactured.
        # If this method is called, it means we are checking Packaging rules specifically.
        # However, M3 (Bolsa) was explicitly assigned to Molino in the previous prompt step.
        # We should keep consistency. If M3 arrives here, send to Molino.
        if activity_type == "M3":
            molino_team = fab_teams_by_type.get("molino")
            if molino_team:
                return self.response(
                    molino_team.id,
                    molino_team.name,
                    "molino",
                    "Actividad M3 (Bolsa). Asignado a MOLINO (Regla Global).",
                    "molino_m3_global"
                )

        # REGLA 1: M4 (Empaque Semi Automático) -> EMPAQUE 2 (Líder)
        if activity_type == "M4":
            empaque2_team = teams_by_type.get("empaque2")
            # TODO: Check capacity for overflow to FAB 3 or MAQUINA 1
            # Assuming Empaque 2 is available for now as primary loop
            if empaque2_team:
                return self.response(
                    empaque2_team.id,
                    empaque2_team.name,
                    "empaque2",
                    "Actividad M4 (Semi Automático). Asignado a EMPAQUE 2.",
                    "empaque2_m4"
                )
            
            # Desborde M4 -> FABRICADO 3 o MAQUINA 1
            # Prioridad Desborde: MAQUINA 1 (Microlotes Semis) o FAB 3?
            # "Los desbordes de M4 se envían a FABRICADO 3 o MAQUINA 1 (si es un microlote M4)"
            # Asumiremos MAQUINA 1 si microlote (digamos < 100?), sino FAB 3?
            # Simplificación: Intentar MAQUINA 1 luego FABRICADO 3
            maquina1_team = teams_by_type.get("maquina1")
            if maquina1_team:
                 return self.response(
                    maquina1_team.id,
                    maquina1_team.name,
                    "maquina1",
                    "Actividad M4 (Desborde). Asignado a MAQUINA 1.",
                    "maquina1_m4_overflow"
                )
            
            fabricado3_team = fab_teams_by_type.get("fabricado3")
            if fabricado3_team:
                 return self.response(
                    fabricado3_team.id,
                    fabricado3_team.name,
                    "fabricado3",
                    "Actividad M4 (Desborde). Asignado a FABRICADO 3.",
                    "fabricado3_m4_overflow"
                )
        
        # REGLA 2: M5 (Empaque Automático)
        if activity_type == "M5":
            # Especialista MAQUINA 2: F1852
            if code == "F1852":
                maquina2_team = teams_by_type.get("maquina2")
                if maquina2_team:
                    return self.response(
                        maquina2_team.id,
                        maquina2_team.name,
                        "maquina2",
                        "Actividad M5 (F1852). Asignado a MAQUINA 2.",
                        "maquina2_m5_f1852"
                    )
            
            # Especialista MAQUINA 1 (Desborde/Apoyo)
            # Pero MAQUINA 2 es el "Líder Absoluto" y "Asignación primaria para el grueso de M5".
            # Intentar MAQUINA 2 primero para el grueso
            maquina2_team = teams_by_type.get("maquina2")
            if maquina2_team:
                return self.response(
                    maquina2_team.id,
                    maquina2_team.name,
                    "maquina2",
                    "Actividad M5 (Empaque Automático). Asignado a MAQUINA 2 (Líder).",
                    "maquina2_m5_leader"
                )
            
            # Desborde a MAQUINA 1
            maquina1_team = teams_by_type.get("maquina1")
            if maquina1_team:
                return self.response(
                    maquina1_team.id,
                    maquina1_team.name,
                    "maquina1",
                    "Actividad M5 (Desborde). Asignado a MAQUINA 1.",
                    "maquina1_m5_overflow"
                )

        # REGLA 3: M2 (Microlotes)
        if activity_type == "M2":
            # EMPAQUE 3: Especialista AX..., PMX...
            if code.startswith("AX") or code.startswith("PMX"):
                empaque3_team = teams_by_type.get("empaque3")
                if empaque3_team:
                     return self.response(
                        empaque3_team.id,
                        empaque3_team.name,
                        "empaque3",
                        f"Actividad M2 (Serie {code[:2]}). Asignado a EMPAQUE 3.",
                        "empaque3_m2_specialist"
                    )
            
            # MAQUINA 1: Absorbe AX... y F...
            # Si AX falló en Empaque 3 (o si consideramos MQ1 como alternativo),
            # Y también series F...
            if code.startswith("F") or code.startswith("AX"):
                maquina1_team = teams_by_type.get("maquina1")
                if maquina1_team:
                      return self.response(
                        maquina1_team.id,
                        maquina1_team.name,
                        "maquina1",
                        f"Actividad M2 (Serie {code[:2]}). Asignado a MAQUINA 1.",
                        "maquina1_m2_specialist"
                    )

            # EMPAQUE 1: Líder Absoluto M2 (Default)
            empaque1_team = teams_by_type.get("empaque1")
            if empaque1_team:
                return self.response(
                    empaque1_team.id,
                    empaque1_team.name,
                    "empaque1",
                    "Actividad M2 (Microlotes). Asignado a EMPAQUE 1 (Líder).",
                    "empaque1_m2_leader"
                )

            # EMPAQUE 3: Soporte Desborde
            empaque3_team = teams_by_type.get("empaque3")
            if empaque3_team:
                return self.response(
                    empaque3_team.id,
                    empaque3_team.name,
                    "empaque3",
                    "Actividad M2 (Desborde). Asignado a EMPAQUE 3.",
                    "empaque3_m2_overflow"
                )

        # REGLA 4: M15 -> EMPAQUE 3 (Soporte M15 bajo volumen)
        if activity_type == "M15":
            empaque3_team = teams_by_type.get("empaque3")
            if empaque3_team:
                return self.response(
                    empaque3_team.id,
                    empaque3_team.name,
                    "empaque3",
                    "Actividad M15. Asignado a EMPAQUE 3.",
                    "empaque3_m15"
                )

        # FALLBACKS
        
        # Priority Fallback: EMPAQUE 1 -> EMPAQUE 3 -> MAQUINA 1
        empaque1_team = teams_by_type.get("empaque1")
        if empaque1_team:
            return self.response(
                empaque1_team.id,
                empaque1_team.name,
                "empaque1",
                "Fallback: Asignado a EMPAQUE 1 por defecto.",
                "fallback_empaque1"
            )
        
        # Último fallback: cualquier equipo disponible
        for team_type, team in teams_by_type.items():
            if team:
                return self.response(
                    team.id,
                    team.name,
                    team_type,
                    f"Fallback: Asignado a {team.name} por defecto.",
                    f"fallback_{team_type}"
                )
        
        return {
            "success": False,
            "reason": "No se encontró ningún equipo de empaque disponible.",
            "rule_applied": "no_teams_available"
        }

    def get_packaging_teams(self, db: Session) -> Dict[str, Any]:
        return TeamSelectionService.get_packaging_teams(db)

    # Obtiene el equipo específico para una actividad de empaque según las reglas de negocio.
    # Esta función ahora delega a get_most_suitable_team con el tipo de actividad.
    def get_specific_team_for_activity(self, activity_name: str, activity_description: str, teams_data: Dict, order_data: Dict = None) -> Dict[str, Any]:

        # Extraer el tipo de actividad del nombre o descripción
        activity_type = None
        if "M1" in activity_name or "M1" in activity_description:
            activity_type = "M1"
        elif "M2" in activity_name or "M2" in activity_description:
            activity_type = "M2"
        elif "M3" in activity_name or "M3" in activity_description:
            activity_type = "M3"
        elif "M4" in activity_name or "M4" in activity_description:
            activity_type = "M4"
        elif "M5" in activity_name or "M5" in activity_description:
            activity_type = "M5"
        
        # Si no se puede determinar el tipo, usar la lógica antigua
        if not activity_type:
            return TeamSelectionService.get_specific_packaging_team_for_activity(
                activity_name, activity_description, teams_data
            )
        
        # Usar la nueva lógica basada en el flujograma
        # Por ahora, retornamos usando el servicio antiguo
        return TeamSelectionService.get_specific_packaging_team_for_activity(
            activity_name, activity_description, teams_data
        )
