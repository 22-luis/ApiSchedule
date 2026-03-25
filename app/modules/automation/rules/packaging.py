import datetime
from typing import Dict, Any, Optional, Set, List

from sqlalchemy.orm import Session
from app.shared.utils.core.time_utils import TimeZoneUtils

from app.modules.automation.rules.base_rule import BaseAutomationRule
from app.modules.automation.services.config import ServiceType
from app.modules.automation.services.utils.team_selection_service import TeamSelectionService
from app.shared.core.enums import PackagingActivities


class PackagingRule(BaseAutomationRule):
    
    @property
    def service_type(self) -> ServiceType:
        return ServiceType.PACKAGING

    @property
    def activity_list_key(self) -> str:
        return "packaging_activities"

    @property
    def excluded_types(self) -> Set[str]:
        # Excluimos M9, M10, M11. 
        # M12, M13, M15 se agregaron a permitidos según requerimiento "Resto".
        return {"M9", "M10", "M11"}

    @property
    def allowed_types(self) -> Set[str]:
        return {"M1", "M2", "M3", "M4", "M5", "M12", "M13", "M15"}

    @property
    def priority_keywords_groups(self) -> List[List[str]]:
        return [
            [PackagingActivities.EMP_GRUPO.value],
            [PackagingActivities.EMP_MANUAL.value],
            [PackagingActivities.EMP_SEMI.value],
            [PackagingActivities.EMP_AUTO.value],
            [PackagingActivities.EMP_MEZCLA.value]
        ]

    @staticmethod
    def _log_debug(message: str):
        try:
            with open("debug_rules.log", "a") as f:
                timestamp = TimeZoneUtils.get_now().isoformat()
                f.write(f"[{timestamp}] {message}\n")
        except (PermissionError, IOError):
            pass

    def get_most_suitable_team(self, db: Session, order_data: Dict = None, activity_type: Optional[str] = None) -> Dict[str, Any]:
    
        code = order_data.get("code", "") if order_data else ""
        quantity = order_data.get("quantity", 0) if order_data else 0
        
        self._log_debug(f"Input: Type={activity_type}, Qty={quantity}, Code={code}")

        # Obtener todos los equipos disponibles
        packaging_teams = TeamSelectionService.get_packaging_teams(db)
        fabrication_teams = TeamSelectionService.get_fabrication_teams(db)
        
        teams_by_type = packaging_teams.get("teams_by_type", {})
        fab_teams_by_type = fabrication_teams.get("teams_by_type", {})
        
        # --- B. REGLAS PRINCIPALES (POR TIPO Y VOLUMEN) ---

        # 1. M1 (Empaque Manual/Especial) -> FABRICADO 3
        if activity_type == "M1":
            fabricado3_team = fab_teams_by_type.get("fabricado3")
            if fabricado3_team:
                return self.response(
                    fabricado3_team.id,
                    fabricado3_team.name,
                    "fabricado3",
                    "Actividad M1 -> Asignado a FABRICADO 3.",
                    "m1_fabricado3"
                )

        # 2. M5 (Empaque Industrial)
        if activity_type == "M5":
            # Cantidad > 1000 -> MAQUINA 1 (o MAQUINA 2)
            if quantity >= 600:
                maquina1_team = teams_by_type.get("maquina1")
                if maquina1_team:
                    return self.response(
                        maquina1_team.id,
                        maquina1_team.name,
                        "maquina1",
                        "Actividad M5 (>600) -> Asignado a MAQUINA 1.",
                        "m5_high_maquina1"
                    )
                # Desborde a MAQUINA 2
                maquina2_team = teams_by_type.get("maquina2")
                if maquina2_team:
                    return self.response(
                        maquina2_team.id,
                        maquina2_team.name,
                        "maquina2",
                        "Actividad M5 (>=600 Desborde) -> Asignado a MAQUINA 2.",
                        "m5_high_maquina2_overflow"
                    )
            
            # Cantidad <= 300 -> EMPAQUE 1 (o EMPAQUE 3)
            # Priorizamos Empaque 1, si no existe o algo, Empaque 3.
            if quantity <= 300:
                 empaque1_team = teams_by_type.get("empaque1")
                 if empaque1_team:
                      return self.response(
                        empaque1_team.id,
                        empaque1_team.name,
                        "empaque1",
                        "Actividad M5 (<=300) -> Asignado a EMPAQUE 1.",
                        "m5_low_empaque1"
                    )
                 # Overflow a Empaque 3
                 empaque3_team = teams_by_type.get("empaque3") or self._find_team_by_name(teams_by_type, "EMPAQUE 3")
                 if empaque3_team:
                      return self.response(
                        empaque3_team.id,
                        empaque3_team.name,
                        "empaque3",
                        "Actividad M5 (<=300) -> Asignado a EMPAQUE 3.",
                        "m5_low_empaque3"
                    )

        # 3. M4 / M2 (Volumen Alto): Si Cantidad > 800 -> EMPAQUE 2
        if activity_type in ["M4", "M2"] and quantity < 800:
            empaque2_team = teams_by_type.get("empaque2")
            if empaque2_team:
                return self.response(
                    empaque2_team.id,
                    empaque2_team.name,
                    "empaque2",
                    f"Actividad {activity_type} (<800) -> Asignado a EMPAQUE 2.",
                    f"{activity_type.lower()}_low_empaque2"
                )

        # --- C. REGLA "RESTO" (POR DEFECTO) ---
        # Lotes pequeños, M2 < 200, M4 <= 800, M5 (300-1000), M12, M13, M15 -> EMPAQUE 1
        
        empaque1_team = teams_by_type.get("empaque1")
        if empaque1_team:
             return self.response(
                empaque1_team.id,
                empaque1_team.name,
                "empaque1",
                f"Resto ({activity_type}, Q={quantity}) -> Asignado a EMPAQUE 1.",
                "rest_empaque1"
            )

        # --- D. FALLBACK ---
        # Si los equipos principales no existen, intenta: EMPAQUE 3 > MAQUINA 1.
        
        # Fallback 1: EMPAQUE 3
        empaque3_team = teams_by_type.get("empaque3") or self._find_team_by_name(teams_by_type, "EMPAQUE 3")
        if empaque3_team:
             return self.response(
                empaque3_team.id,
                empaque3_team.name,
                "empaque3",
                "Fallback: Asignado a EMPAQUE 3.",
                "fallback_empaque3"
            )
            
        # Fallback 2: MAQUINA 1
        maquina1_team = teams_by_type.get("maquina1")
        if maquina1_team:
             return self.response(
                maquina1_team.id,
                maquina1_team.name,
                "maquina1",
                "Fallback: Asignado a MAQUINA 1.",
                "fallback_maquina1"
            )

        return {
            "success": False,
            "reason": "No se encontró ningún equipo de empaque disponible para la regla aplicada.",
            "rule_applied": "no_teams_available"
        }

    @staticmethod
    def _find_team_by_name(teams_dict, name_part):
        for t in teams_dict.values():
            if name_part in t.name.upper():
                return t
        return None

    @staticmethod
    def get_packaging_teams(db: Session) -> Dict[str, Any]:
        return TeamSelectionService.get_packaging_teams(db)

    # Obtiene el equipo específico para una actividad de empaque según las reglas de negocio.
    # Esta función ahora delega a get_most_suitable_team con el tipo de actividad.
    @staticmethod
    def get_specific_team_for_activity(activity_name: str, activity_description: str, teams_data: Dict) -> Dict[str, Any]:

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

    def get_candidate_teams(self, db: Session, order_data: Dict, activity_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Devuelve una lista de equipos candidatos en orden de prioridad para la asignación de empaque.
        """
        candidates = []
        quantity = order_data.get("quantity", 0) if order_data else 0
        
        # Obtener todos los equipos disponibles
        packaging_teams = TeamSelectionService.get_packaging_teams(db)
        fabrication_teams = TeamSelectionService.get_fabrication_teams(db)
        
        teams_by_type = packaging_teams.get("teams_by_type", {})
        fab_teams_by_type = fabrication_teams.get("teams_by_type", {})
        
        def add_candidate(team, rule_name, reason):
            if team:
                candidates.append({
                    "id": team.id,
                    "name": team.name,
                    "priority_rule": rule_name,
                    "reason": reason,
                    "team_obj": team
                })

        # --- REGLAS PRINCIPALES ---

        # 1. M1 -> FABRICADO 3
        if activity_type == "M1":
            add_candidate(fab_teams_by_type.get("fabricado3"), "m1_fabricado3", "Actividad M1")
            return candidates

        # 2. M5
        if activity_type == "M5":
            if quantity >= 600:
                add_candidate(teams_by_type.get("maquina1"), "m5_high_maquina1", "Actividad M5 >= 600 (Prioridad 1)")
                add_candidate(teams_by_type.get("maquina2"), "m5_high_maquina2_overflow", "Actividad M5 >= 600 (Prioridad 2 - Desborde)")
                return candidates
            
            if quantity <= 300:
                add_candidate(teams_by_type.get("empaque1"), "m5_low_empaque1", "Actividad M5 <= 300 (Prioridad 1)")
                add_candidate(teams_by_type.get("empaque3") or self._find_team_by_name(teams_by_type, "EMPAQUE 3"), "m5_low_empaque3", "Actividad M5 <= 300 (Prioridad 2 - Desborde)")
                return candidates

        # 3. M4 / M2 (< 800) -> EMPAQUE 2
        if activity_type in ["M4", "M2"] and quantity < 800:
            add_candidate(teams_by_type.get("empaque2"), f"{activity_type.lower()}_low_empaque2", f"Actividad {activity_type} < 800")
            add_candidate(teams_by_type.get("empaque1"), "overflow_empaque1", "Desborde a Empaque 1")
            return candidates

        # --- RESTO / DEFAULT ---
        # "Resto" -> Empaque 1. Agregamos desbordes a Empaque 3 y Maquina 1 como fallbacks.
        add_candidate(teams_by_type.get("empaque1"), "rest_empaque1", "Resto/Default (Prioridad 1)")
        add_candidate(teams_by_type.get("empaque3") or self._find_team_by_name(teams_by_type, "EMPAQUE 3"), "fallback_empaque3", "Resto/Default (Prioridad 2 - Desborde)")
        add_candidate(teams_by_type.get("maquina1"), "fallback_maquina1", "Resto/Default (Prioridad 3 - Desborde)")
        
        return candidates
