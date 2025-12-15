from typing import Dict, Any, Optional, Set, List
from sqlalchemy.orm import Session
import datetime

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
        # Excluimos M9, M10, M11. 
        # M12, M13, M15 se agregaron a permitidos segun requerimiento "Resto".
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

    def _log_debug(self, message: str):
        try:
            with open("debug_rules.log", "a") as f:
                timestamp = datetime.datetime.now().isoformat()
                f.write(f"[{timestamp}] {message}\n")
        except:
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
        
        self._log_debug(f"Available Packaging Teams Keys: {list(teams_by_type.keys())}")

        # --- REGLAS ESPECIALES HISTÓRICAS ---
        # Si M3 (Bolsa) sigue yendo a Molino, lo conservamos.
        if activity_type == "M3":
            molino_team = fab_teams_by_type.get("molino")
            if molino_team:
                return self.response(
                    molino_team.id,
                    molino_team.name,
                    "molino",
                    "Actividad M3 (Bolsa). Asignado a MOLINO.",
                    "molino_m3_global"
                )

        # --- NUEVAS REGLAS DE FILTRADO ---

        # 1. Filtro M1: Si es M1 -> EMPAQUE 4.
        if activity_type == "M1":
            empaque4_team = teams_by_type.get("empaque4")
            if empaque4_team:
                return self.response(
                    empaque4_team.id,
                    empaque4_team.name,
                    "empaque4",
                    "Actividad M1 -> Asignado a EMPAQUE 4.",
                    "m1_empaque4"
                )

        # 2. Filtro M5 (Industrial): Si es M5 y > 1000 -> MAQUINA 1 (o 2 por desborde).
        if activity_type == "M5":
            if quantity > 1000:
                maquina1_team = teams_by_type.get("maquina1")
                if maquina1_team:
                    return self.response(
                        maquina1_team.id,
                        maquina1_team.name,
                        "maquina1",
                        "Actividad M5 (>1000) -> Asignado a MAQUINA 1.",
                        "m5_high_maquina1"
                    )
                # Desborde a MAQUINA 2
                maquina2_team = teams_by_type.get("maquina2")
                if maquina2_team:
                    return self.response(
                        maquina2_team.id,
                        maquina2_team.name,
                        "maquina2",
                        "Actividad M5 (>1000 Desborde) -> Asignado a MAQUINA 2.",
                        "m5_high_maquina2_overflow"
                    )
            # Si es M5 <= 1000, cae al RESTO -> EMPAQUE 1

        # 3. Filtro Volumen Alto (M4/M2): Si la cantidad > 800 -> EMPAQUE 2.
        if activity_type in ["M4", "M2"]:
            if quantity > 800:
                empaque2_team = teams_by_type.get("empaque2")
                if empaque2_team:
                    return self.response(
                        empaque2_team.id,
                        empaque2_team.name,
                        "empaque2",
                        f"Actividad {activity_type} (>800) -> Asignado a EMPAQUE 2.",
                        f"{activity_type.lower()}_high_empaque2"
                    )

        # 4. Filtro Volumen Medio (M2): Si es M2 y está entre 200 y 800 -> EMPAQUE 3.
        if activity_type == "M2":
            if 200 <= quantity <= 800:
                self._log_debug("Matching M2 Medium Volume Rule (200-800)")
                empaque3_team = teams_by_type.get("empaque3")
                
                # Robust search if key missing but team exists
                if not empaque3_team:
                    for t in teams_by_type.values():
                        if "EMPAQUE 3" in t.name.upper():
                            empaque3_team = t
                            break
                
                if empaque3_team:
                    self._log_debug(f"Assigned to {empaque3_team.name}")
                    return self.response(
                        empaque3_team.id,
                        empaque3_team.name,
                        "empaque3",
                        "Actividad M2 (200-800) -> Asignado a EMPAQUE 3.",
                        "m2_med_empaque3"
                    )
                else:
                    self._log_debug("Empaque 3 team NOT FOUND.")

        # 5. Resto: Todo lo demás (lotes pequeños, M13, M12, M5 pequeños) -> EMPAQUE 1.
        # Esto incluye M2 < 200, M4 <= 800, M5 <= 1000, M12, M13, M15, etc.
        empaque1_team = teams_by_type.get("empaque1")
        if empaque1_team:
            self._log_debug("Assigned to Empaque 1 (Resto)")
            return self.response(
                empaque1_team.id,
                empaque1_team.name,
                "empaque1",
                f"Resto ({activity_type}, Q={quantity}) -> Asignado a EMPAQUE 1.",
                "rest_empaque1"
            )

        # FALLBACKS si los equipos destino no existen
        self._log_debug("Fallback triggered")
        for fallback_team_type in ["empaque3", "maquina1"]:
            fallback_team = teams_by_type.get(fallback_team_type)
            if fallback_team:
                 return self.response(
                    fallback_team.id,
                    fallback_team.name,
                    fallback_team_type,
                    f"Fallback General ({activity_type}) -> Asignado a {fallback_team.name}.",
                    f"fallback_{fallback_team_type}"
                )
        
        return {
            "success": False,
            "reason": "No se encontró ningún equipo de empaque disponible para la regla aplicada.",
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
